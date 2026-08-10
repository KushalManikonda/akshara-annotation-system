"""
backend/api/routers/queue.py
----------------------------
Task Queue & Self-Assignment API

Endpoints:
  GET  /queue/stats          — Full queue statistics (global + per-language)
  POST /queue/assign         — Atomically assign next available task (SKIP LOCKED)
  GET  /queue/my-tasks       — Current annotator's tasks grouped by status
  POST /queue/heartbeat/{id} — Extend task keep-alive (prevents auto-release)

Concurrency guarantee:
  SELECT FOR UPDATE SKIP LOCKED ensures that even when dozens of annotators
  click "Generate Task" simultaneously, each gets a unique task.
  No Python-level locking or retry logic is required.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text, func
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user, get_db, require_role
from database.models import AudioFile, Dataset, AuditLog, User
from database.enums import AudioStatus, UserRole, AuditAction

logger = logging.getLogger("akshara.queue")

router = APIRouter(prefix="/queue", tags=["queue"])

# ── Configurable timeouts ────────────────────────────────────────────────────
ASSIGNED_TIMEOUT_MINUTES = 20    # ASSIGNED but never opened → release
IN_PROGRESS_TIMEOUT_MINUTES = 45  # IN_PROGRESS with no heartbeat → release


# ── Pydantic schemas ─────────────────────────────────────────────────────────

class AssignRequest(BaseModel):
    language: str  # Language name or "any"


class LanguageStat(BaseModel):
    language: str
    available: int


class QueueStats(BaseModel):
    total_unassigned: int
    total_assigned: int
    total_in_progress: int
    total_submitted: int
    total_rework_required: int
    total_completed_today: int
    per_language: List[LanguageStat]


class TaskSummary(BaseModel):
    id: str
    filename: str
    original_filename: str
    language: str
    duration: Optional[float]
    status: str
    audio_url: Optional[str]
    assigned_at: Optional[datetime]

    class Config:
        from_attributes = True


class MyTasksResponse(BaseModel):
    rework_required: List[TaskSummary]
    in_progress: List[TaskSummary]
    assigned: List[TaskSummary]
    submitted: List[TaskSummary]
    completed_today: List[TaskSummary]


# ── Helper ────────────────────────────────────────────────────────────────────

def _audio_to_summary(af: AudioFile) -> TaskSummary:
    return TaskSummary(
        id=af.id,
        filename=af.filename,
        original_filename=af.original_filename,
        language=af.language,
        duration=af.duration,
        status=af.status.value if hasattr(af.status, "value") else af.status,
        audio_url=af.audio_url,
        assigned_at=af.assigned_at,
    )


def _log_audit(db: Session, user_id: str, action: AuditAction, details: str):
    try:
        log = AuditLog(user_id=user_id, action=action, details=details)
        db.add(log)
        # Don't commit here — caller handles the transaction
    except Exception:
        logger.warning(f"Failed to write audit log: {action} for user {user_id}")


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=QueueStats)
def get_queue_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns full queue statistics.
    - Global counts per status
    - Per-language count of UNASSIGNED tasks
    """
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    def count_status(status: AudioStatus) -> int:
        return db.query(func.count(AudioFile.id)).filter(
            AudioFile.status == status
        ).scalar() or 0

    per_language = (
        db.query(AudioFile.language, func.count(AudioFile.id))
        .filter(AudioFile.status == AudioStatus.UNASSIGNED)
        .group_by(AudioFile.language)
        .order_by(func.count(AudioFile.id).desc())
        .all()
    )

    completed_today = db.query(func.count(AudioFile.id)).filter(
        AudioFile.status == AudioStatus.COMPLETED,
        AudioFile.last_heartbeat_at >= today_start,  # proxy for completion time
    ).scalar() or 0

    return QueueStats(
        total_unassigned=count_status(AudioStatus.UNASSIGNED),
        total_assigned=count_status(AudioStatus.ASSIGNED),
        total_in_progress=count_status(AudioStatus.IN_PROGRESS),
        total_submitted=count_status(AudioStatus.SUBMITTED),
        total_rework_required=count_status(AudioStatus.REWORK_REQUIRED),
        total_completed_today=completed_today,
        per_language=[LanguageStat(language=lang, available=cnt) for lang, cnt in per_language],
    )


@router.post("/assign", response_model=TaskSummary)
def assign_task(
    payload: AssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ANNOTATOR)),
):
    """
    Atomically assigns the next available task to the calling annotator.

    Priority order:
      1. Highest dataset priority DESC
      2. Oldest uploaded_at ASC (FIFO)
      3. Language filter

    Uses SELECT FOR UPDATE SKIP LOCKED to guarantee:
      - No duplicate assignments even under concurrent load
      - Two annotators requesting the same language get different tasks
    """
    # ── 1. Rework tasks take priority ────────────────────────────────────────
    rework = (
        db.query(AudioFile)
        .filter(
            AudioFile.assigned_to == current_user.id,
            AudioFile.status == AudioStatus.REWORK_REQUIRED,
        )
        .first()
    )
    if rework:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "REWORK_PENDING",
                "message": "You have tasks that need rework. Please complete those first.",
                "task_id": rework.id,
                "task_filename": rework.original_filename,
            },
        )

    # ── 2. Prevent annotator from holding too many ASSIGNED tasks ────────────
    already_assigned = (
        db.query(func.count(AudioFile.id))
        .filter(
            AudioFile.assigned_to == current_user.id,
            AudioFile.status.in_([AudioStatus.ASSIGNED, AudioStatus.IN_PROGRESS]),
        )
        .scalar() or 0
    )
    if already_assigned >= 5:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "TOO_MANY_ACTIVE",
                "message": "You already have 5 active tasks. Please complete some before requesting more.",
            },
        )

    # ── 3. Build base query with SKIP LOCKED ─────────────────────────────────
    # We must use raw SQL for FOR UPDATE SKIP LOCKED since SQLAlchemy ORM
    # doesn't expose SKIP LOCKED natively in all versions.
    lang_filter = ""
    params: dict = {"user_id": current_user.id, "now": datetime.utcnow()}

    if payload.language.lower() != "any":
        lang_filter = "AND af.language = :language"
        params["language"] = payload.language

    raw_sql = text(f"""
        SELECT af.id
        FROM audio_files af
        JOIN datasets d ON d.id = af.dataset_id
        WHERE af.status = 'UNASSIGNED'
        {lang_filter}
        ORDER BY d.priority DESC, af.uploaded_at ASC
        LIMIT 1
        FOR UPDATE OF af SKIP LOCKED
    """)

    row = db.execute(raw_sql, params).fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NO_TASKS_AVAILABLE",
                "message": (
                    f"No tasks are currently available"
                    f"{' for ' + payload.language if payload.language.lower() != 'any' else ''}."
                ),
            },
        )

    audio_id = row[0]

    # ── 4. Assign the task ────────────────────────────────────────────────────
    audio = db.query(AudioFile).filter(AudioFile.id == audio_id).first()
    audio.status = AudioStatus.ASSIGNED
    audio.assigned_to = current_user.id
    audio.assigned_at = datetime.utcnow()
    audio.last_heartbeat_at = datetime.utcnow()

    _log_audit(
        db, current_user.id, AuditAction.TASK_ASSIGNED,
        f"Task {audio_id} ({audio.original_filename}) assigned to {current_user.username}"
    )

    db.commit()
    db.refresh(audio)

    logger.info(f"Task {audio_id} assigned to annotator {current_user.id}")
    return _audio_to_summary(audio)


@router.get("/my-tasks", response_model=MyTasksResponse)
def get_my_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ANNOTATOR)),
):
    """
    Returns the calling annotator's current tasks, grouped by status.
    """
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    def fetch(statuses, extra_filter=None):
        q = db.query(AudioFile).filter(
            AudioFile.assigned_to == current_user.id,
            AudioFile.status.in_(statuses),
        )
        if extra_filter is not None:
            q = q.filter(extra_filter)
        return [_audio_to_summary(a) for a in q.order_by(AudioFile.assigned_at.asc()).all()]

    return MyTasksResponse(
        rework_required=fetch([AudioStatus.REWORK_REQUIRED]),
        in_progress=fetch([AudioStatus.IN_PROGRESS]),
        assigned=fetch([AudioStatus.ASSIGNED]),
        submitted=fetch([AudioStatus.SUBMITTED]),
        completed_today=fetch(
            [AudioStatus.COMPLETED],
            AudioFile.last_heartbeat_at >= today_start,
        ),
    )


@router.post("/heartbeat/{audio_id}")
def heartbeat(
    audio_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ANNOTATOR)),
):
    """
    Extends the task's keep-alive timestamp.
    Called every 30s by the annotation workspace.
    Prevents the auto-release background job from reclaiming the task.
    """
    audio = db.query(AudioFile).filter(AudioFile.id == audio_id).first()

    if not audio:
        raise HTTPException(status_code=404, detail="Task not found")

    if audio.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this task")

    raw_status = getattr(audio.status, "value", audio.status)
    status_str = str(raw_status).upper()

    if status_str not in ("ASSIGNED", "IN_PROGRESS", "REWORK_REQUIRED"):
        raise HTTPException(status_code=409, detail=f"Task is in terminal state: {status_str}")

    audio.last_heartbeat_at = datetime.utcnow()
    db.commit()

    return {"ok": True, "next_heartbeat_in_seconds": 30}

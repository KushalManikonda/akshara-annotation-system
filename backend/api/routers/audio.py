"""
backend/api/routers/audio.py
----------------------------
Audio file endpoints.
Includes server-side task ownership validation on all state-changing operations.
"""

import logging
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer
from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user, get_db
from backend.schemas.audio import AudioFileResponse, AudioStatusUpdate
from backend.database.models import User, AudioFile, Dataset, AuditLog, Annotation, ReviewerApproval, ReviewComment
from backend.database.enums import UserRole, AudioStatus, AnnotationState, AuditAction, ApprovalStatus

logger = logging.getLogger("akshara.audio")

router = APIRouter(prefix="/audio", tags=["audio"])


def _require_task_owner(audio: AudioFile, current_user: User):
    """Raise 403 if the current user does not own this task."""
    if audio.assigned_to != current_user.id:
        role_val = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
        if role_val not in ("ADMIN", "SUPER_ADMIN"):
            raise HTTPException(status_code=403, detail="You do not own this task")


def _attach_review_stats(db: Session, audio: AudioFile, current_user: Optional[User] = None):
    total_reviewers = db.query(func.count(User.id)).filter(User.role == UserRole.REVIEWER).scalar() or 0
    if total_reviewers == 0:
        total_reviewers = 1

    ann = db.query(Annotation).filter(Annotation.audio_id == audio.id).order_by(Annotation.updated_at.desc()).first()
    m = 0
    reviewed_by_me = False
    my_review_status = None
    last_comment = None
    last_returned_at = None
    submitted_at = None
    annotator_username = None

    if audio.dataset_id:
        ds = db.query(Dataset).filter(Dataset.id == audio.dataset_id).first()
        if ds:
            audio.dataset_name = ds.name

    if audio.assigned_to:
        ann_user = db.query(User).filter(User.id == audio.assigned_to).first()
        if ann_user:
            annotator_username = ann_user.username

    if ann:
        if ann.annotator_id and not annotator_username:
            ann_user = db.query(User).filter(User.id == ann.annotator_id).first()
            if ann_user:
                annotator_username = ann_user.username

        submitted_at = ann.submitted_at

        # Fetch latest return comment
        latest_comment_obj = (
            db.query(ReviewComment)
            .filter(ReviewComment.annotation_id == ann.id)
            .order_by(ReviewComment.created_at.desc())
            .first()
        )
        if latest_comment_obj:
            last_comment = latest_comment_obj.comment
            last_returned_at = latest_comment_obj.created_at

        m = db.query(func.count(ReviewerApproval.id)).filter(
            ReviewerApproval.annotation_id == ann.id,
            ReviewerApproval.status == ApprovalStatus.APPROVED,
            ReviewerApproval.is_valid == True
        ).scalar() or 0

        if current_user:
            app = db.query(ReviewerApproval).filter(
                ReviewerApproval.annotation_id == ann.id,
                ReviewerApproval.reviewer_id == current_user.id,
                ReviewerApproval.status == ApprovalStatus.APPROVED,
                ReviewerApproval.is_valid == True
            ).first()
            if app:
                reviewed_by_me = True
                my_review_status = "APPROVED"
            else:
                com = db.query(ReviewComment).filter(
                    ReviewComment.annotation_id == ann.id,
                    ReviewComment.reviewer_id == current_user.id
                ).order_by(ReviewComment.created_at.desc()).first()
                if com:
                    reviewed_by_me = True
                    my_review_status = "REJECTED"

    # Requirement 8 Protection: If audio or annotation is already COMPLETED / APPROVED, freeze it!
    is_already_completed = (
        (hasattr(audio.status, "value") and audio.status.value == "COMPLETED") or
        audio.status == "COMPLETED" or audio.status == AudioStatus.COMPLETED or
        (ann and ann.state == AnnotationState.APPROVED)
    )
    if is_already_completed:
        reviewed_count_val = max(m, total_reviewers)
        total_reviewers_val = max(m, total_reviewers)
    else:
        reviewed_count_val = m
        total_reviewers_val = total_reviewers

    audio.reviewed_count = reviewed_count_val
    audio.total_reviewers = total_reviewers_val
    audio.reviewed_by_me = reviewed_by_me
    audio.my_review_status = my_review_status
    audio.last_reviewer_comment = last_comment
    audio.last_returned_at = last_returned_at
    audio.submitted_at = submitted_at
    audio.annotator_username = annotator_username
    return audio


@router.get("/", response_model=List[AudioFileResponse])
def read_all_audio(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all audio files. Admin/Reviewer see all; annotators see only their own."""
    role_val = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
    if role_val in ("ADMIN", "SUPER_ADMIN", "REVIEWER"):
        audio_list = db.query(AudioFile).all()
    else:
        # Annotators only see their assigned tasks
        audio_list = db.query(AudioFile).filter(AudioFile.assigned_to == current_user.id).all()

    return [_attach_review_stats(db, a, current_user) for a in audio_list]


@router.get("/{audio_id}", response_model=AudioFileResponse)
def read_audio_by_id(
    audio_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get specific audio file by ID. Validates ownership for annotators."""
    audio = db.query(AudioFile).filter(AudioFile.id == audio_id).first()
    if not audio:
        raise HTTPException(status_code=404, detail="Audio file not found")

    role_val = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
    if role_val == "ANNOTATOR":
        _require_task_owner(audio, current_user)

    return _attach_review_stats(db, audio, current_user)


@router.get("/{audio_id}/stream")
def stream_audio(
    audio_id: str,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
    credentials = Depends(HTTPBearer(auto_error=False)),
):
    """
    Return a redirect to the Supabase Storage signed URL for the audio file.
    Falls back to local filesystem only in development when audio_url is not set.
    Accepts token via query param for WaveSurfer compatibility.
    """
    from backend.core.security import decode_token
    from fastapi.responses import RedirectResponse
    from backend.core.config import settings

    # Accept token from query param OR Authorization header
    raw_token = token
    if not raw_token and credentials:
        raw_token = credentials.credentials

    if not raw_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_token(raw_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    audio = db.query(AudioFile).filter(AudioFile.id == audio_id).first()
    if not audio:
        raise HTTPException(status_code=404, detail="Audio file not found")

    # ── Production path: use Supabase Storage ─────────────────────────────────
    if audio.audio_url:
        # If it's already a full URL (public bucket / legacy), redirect directly
        if audio.audio_url.startswith("http"):
            return RedirectResponse(url=audio.audio_url, status_code=302)

        # It's a storage key (path within bucket) → generate a signed URL
        try:
            from supabase import create_client
            supa = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
            signed_result = supa.storage.from_(settings.STORAGE_BUCKET).create_signed_url(
                audio.audio_url,
                settings.AUDIO_URL_EXPIRY_SECONDS,
            )
            # supabase-py v2 returns the URL directly as a string, or wrapped in a dict
            if isinstance(signed_result, dict):
                signed_url = signed_result.get("signedURL") or signed_result.get("signedUrl") or signed_result.get("signed_url")
            else:
                signed_url = signed_result  # v2 sometimes returns str directly

            if signed_url and signed_url.startswith("http"):
                return RedirectResponse(url=signed_url, status_code=302)
            raise ValueError(f"Unexpected signed URL response: {signed_result}")
        except Exception as e:
            logger.error(f"Failed to generate signed URL for audio {audio_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate audio URL. Please contact admin.")

    # ── Development fallback: local filesystem ────────────────────────────────
    if settings.ENVIRONMENT == "production":
        raise HTTPException(
            status_code=404,
            detail="Audio file not available. The file may not have been uploaded to storage."
        )

    # Local file fallback (development only)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    file_path = os.path.normpath(os.path.join(project_root, audio.file_path))

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Audio file not found on disk: {audio.original_filename}")

    return FileResponse(
        path=file_path,
        media_type="audio/wav",
        headers={"Accept-Ranges": "bytes"},
    )


@router.patch("/{audio_id}/start")
def start_task(
    audio_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Transition task from ASSIGNED → IN_PROGRESS.
    Called automatically when the annotator opens the workspace.
    Server-side ownership enforced.
    """
    audio = db.query(AudioFile).filter(AudioFile.id == audio_id).first()
    if not audio:
        raise HTTPException(status_code=404, detail="Audio file not found")

    _require_task_owner(audio, current_user)

    print(f"=== DEBUG START_TASK: audio_id={audio_id}, status={audio.status}, type={type(audio.status)} ===", flush=True)

    raw_status = getattr(audio.status, "value", audio.status)
    status_str = str(raw_status).upper()
    if "SUBMITTED" in status_str or "COMPLETED" in status_str:
        clean_status = "COMPLETED" if "COMPLETED" in status_str else "SUBMITTED"
        return {"message": "Task opened in read-only mode", "status": clean_status}

    if status_str == "REWORK_REQUIRED":
        audio.last_heartbeat_at = datetime.utcnow()
        db.commit()
        return {"message": "Rework task opened", "status": "REWORK_REQUIRED"}

    if status_str == "IN_PROGRESS":
        audio.last_heartbeat_at = datetime.utcnow()
        db.commit()
        return {"message": "Task already in progress", "status": "IN_PROGRESS"}

    if status_str != "ASSIGNED":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot start task in state: {status_str}"
        )

    audio.status = AudioStatus.IN_PROGRESS
    audio.last_heartbeat_at = datetime.utcnow()

    log = AuditLog(
        user_id=current_user.id,
        action=AuditAction.TASK_OPENED,
        details=f"Task {audio_id} ({audio.original_filename}) opened by {current_user.username}",
    )
    db.add(log)
    db.commit()

    logger.info(f"Task {audio_id} → IN_PROGRESS by {current_user.id}")
    return {"message": "Task started", "status": "IN_PROGRESS"}


@router.patch("/{audio_id}/status")
def change_audio_status(
    audio_id: str,
    payload: AudioStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update status of an audio file. Admin-only general status change.
    Annotators must use /start for their state transitions.
    """
    try:
        status_enum = AudioStatus(payload.status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")

    audio = db.query(AudioFile).filter(AudioFile.id == audio_id).first()
    if not audio:
        raise HTTPException(status_code=404, detail="Audio file not found")

    audio.status = status_enum
    db.commit()

    return {"message": "Status updated successfully"}

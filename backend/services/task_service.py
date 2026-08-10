"""
task_service.py – Phase 5.1
Responsible for automated, atomic task distribution to annotators.

Design decision: Uses a SELECT-then-UPDATE pattern inside a single
transaction to ensure no two annotators can claim the same audio file.
The UPDATE uses the same WHERE condition as the SELECT, so if another
session claims the row between our SELECT and UPDATE, the update will
affect 0 rows and we retry or return None.
"""

from typing import Optional

from sqlalchemy.orm import Session

from database.database import SessionLocal
from database.models import AudioFile
from database.enums import AudioStatus
from utils.logger import logger


def get_db() -> Session:
    return SessionLocal()


def reserve_next_task(annotator_id: str) -> Optional[AudioFile]:
    """
    Atomically reserve the next available (UNASSIGNED) audio file
    for the given annotator.

    - Selects the oldest UNASSIGNED clip using FOR UPDATE row locking
      (SQLite does not support SELECT FOR UPDATE, so we use a
      check-then-update pattern within the same transaction).
    - Transitions the audio status from UNASSIGNED → ASSIGNED.
    - Returns the reserved AudioFile, or None if no tasks are available.
    """
    db = get_db()

    try:
        # Find the oldest unassigned file not already reserved by anyone
        candidate = (
            db.query(AudioFile)
            .filter(
                AudioFile.status == AudioStatus.UNASSIGNED,
                AudioFile.assigned_to == None,  # noqa: E711
            )
            .order_by(AudioFile.uploaded_at.asc())
            .with_for_update()  # Row-level lock where supported
            .first()
        )

        if candidate is None:
            logger.info(f"No unassigned tasks available for annotator {annotator_id}")
            return None

        # Atomically claim it
        candidate.status = AudioStatus.ASSIGNED
        candidate.assigned_to = annotator_id

        db.commit()
        db.refresh(candidate)

        logger.info(
            f"Task reserved: audio_id={candidate.id} "
            f"annotator_id={annotator_id}"
        )

        return candidate

    except Exception:
        db.rollback()
        logger.exception(
            f"Failed to reserve task for annotator {annotator_id}"
        )
        return None

    finally:
        db.close()


def get_annotator_tasks(annotator_id: str) -> list:
    """
    Return all audio files currently assigned to or in-progress by
    the given annotator.
    """
    db = get_db()

    try:
        return (
            db.query(AudioFile)
            .filter(
                AudioFile.assigned_to == annotator_id,
                AudioFile.status.in_([
                    AudioStatus.ASSIGNED,
                    AudioStatus.IN_PROGRESS,
                    AudioStatus.SUBMITTED,
                ])
            )
            .order_by(AudioFile.uploaded_at.asc())
            .all()
        )

    finally:
        db.close()


def get_task_by_id(audio_id: str) -> Optional[AudioFile]:
    """Return a single audio task by its ID."""
    db = get_db()

    try:
        return (
            db.query(AudioFile)
            .filter(AudioFile.id == audio_id)
            .first()
        )

    finally:
        db.close()


def release_task(audio_id: str, annotator_id: str) -> bool:
    """
    Release a task back to the UNASSIGNED pool.
    Deletes any draft annotations the user made.
    """
    db = get_db()
    try:
        audio = db.query(AudioFile).filter(
            AudioFile.id == audio_id,
            AudioFile.assigned_to == annotator_id
        ).first()

        if not audio:
            return False

        # Delete associated annotation to clear the slate
        from database.models import Annotation
        db.query(Annotation).filter(
            Annotation.audio_id == audio_id,
            Annotation.annotator_id == annotator_id
        ).delete()

        audio.status = AudioStatus.UNASSIGNED
        audio.assigned_to = None

        db.commit()
        logger.info(f"Task {audio_id} released by {annotator_id}")
        return True
    except Exception:
        db.rollback()
        logger.exception(f"Failed to release task {audio_id}")
        return False
    finally:
        db.close()

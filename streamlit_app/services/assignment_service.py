from sqlalchemy.orm import Session, joinedload

from database.database import SessionLocal
from database.models import AudioFile, User
from database.enums import AudioStatus, UserRole
from utils.logger import logger


def get_db() -> Session:
    return SessionLocal()


def get_unassigned_audio():

    db = get_db()

    try:
        return (
            db.query(AudioFile)
            .filter(AudioFile.status == AudioStatus.UNASSIGNED)
            .all()
        )

    finally:
        db.close()


def get_annotators():

    db = get_db()

    try:
        return (
            db.query(User)
            .filter(
                User.role == UserRole.ANNOTATOR,
                User.is_active == True
            )
            .all()
        )

    finally:
        db.close()


def assign_audio(audio_id: str, annotator_id: str):

    db = get_db()

    try:

        audio = (
            db.query(AudioFile)
            .filter(AudioFile.id == audio_id)
            .first()
        )

        if not audio:
            return False

        if audio.status != AudioStatus.UNASSIGNED:
            return False

        audio.assigned_to = annotator_id
        audio.status = AudioStatus.ASSIGNED

        db.commit()

        return True

    except Exception:
        db.rollback()
        logger.exception(f"Failed to assign audio {audio_id}")
        return False

    finally:
        db.close()


def get_assignments():

    db = get_db()

    try:

        return (
            db.query(AudioFile)
            .options(
                joinedload(AudioFile.assignee)
            )
            .filter(AudioFile.assigned_to.isnot(None))
            .all()
        )

    finally:
        db.close()


def unassign_audio(audio_id: str):

    db = get_db()

    try:

        audio = (
            db.query(AudioFile)
            .filter(AudioFile.id == audio_id)
            .first()
        )

        if not audio:
            return False

        audio.assigned_to = None
        audio.status = AudioStatus.UNASSIGNED

        db.commit()

        return True

    except Exception:
        db.rollback()
        logger.exception(f"Failed to unassign audio {audio_id}")
        return False

    finally:
        db.close()
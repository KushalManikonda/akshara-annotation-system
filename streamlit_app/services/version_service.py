"""
version_service.py – Phase 7
Provides all database operations related to annotation version history.

Responsibilities:
  - Fetch version list for an annotation.
  - Fetch a specific version snapshot.
  - Restore an annotator's current draft to a past snapshot.
"""

from database.database import SessionLocal
from database.models import AnnotationVersion, Annotation
from database.enums import AnnotationState, AudioStatus
from utils.logger import logger


def get_db():
    return SessionLocal()


def get_versions(annotation_id: str) -> list:
    """
    Return all AnnotationVersion rows for the given annotation,
    sorted from newest (highest version_number) to oldest.
    """
    db = get_db()
    try:
        return (
            db.query(AnnotationVersion)
            .filter(AnnotationVersion.annotation_id == annotation_id)
            .order_by(AnnotationVersion.version_number.desc())
            .all()
        )
    finally:
        db.close()


def get_version(version_id: str):
    """Return a single AnnotationVersion by its primary key."""
    db = get_db()
    try:
        return (
            db.query(AnnotationVersion)
            .filter(AnnotationVersion.id == version_id)
            .first()
        )
    finally:
        db.close()


def restore_version(annotation_id: str, version_id: str) -> bool:
    """
    Overwrite the current annotation draft with the transcript and rsml
    from the chosen historical version.

    Safety rules:
      - Restore is only allowed when the annotation is in DRAFT or RETURNED state.
      - Restoring does NOT change annotation.state or audio.status.
      - A restore is purely a text rollback — the annotator must still
        re-submit manually for the next review round.

    Returns True on success, False on failure.
    """
    db = get_db()
    try:
        annotation = (
            db.query(Annotation)
            .filter(Annotation.id == annotation_id)
            .first()
        )

        if not annotation:
            logger.error(f"Annotation {annotation_id} not found for restore.")
            return False

        # Safety: only allow restore when annotation is editable
        if annotation.state not in [AnnotationState.DRAFT, AnnotationState.RETURNED]:
            logger.warning(
                f"Restore rejected: annotation {annotation_id} is in state "
                f"{annotation.state} (must be DRAFT or RETURNED)."
            )
            return False

        version = (
            db.query(AnnotationVersion)
            .filter(
                AnnotationVersion.id == version_id,
                AnnotationVersion.annotation_id == annotation_id,
            )
            .first()
        )

        if not version:
            logger.error(
                f"Version {version_id} not found for annotation {annotation_id}."
            )
            return False

        annotation.transcript = version.transcript_snapshot
        annotation.rsml_content = version.rsml_snapshot

        db.commit()
        logger.info(
            f"Annotation {annotation_id} restored to v{version.version_number} "
            f"(version_id={version_id})."
        )
        return True

    except Exception:
        db.rollback()
        logger.exception(
            f"Failed to restore annotation {annotation_id} to version {version_id}"
        )
        return False

    finally:
        db.close()

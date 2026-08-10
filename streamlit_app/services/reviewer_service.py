"""
reviewer_service.py – Phase 6
Handles all reviewer-side business logic.

Consensus Approval Rule:
    An annotation is only truly APPROVED (frozen) when EVERY active reviewer
    in the system has individually approved it for the current submission
    version. Until then the annotation remains in SUBMITTED state with
    individual approval records tracked in ReviewerApproval.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy.orm import Session, joinedload

from database.database import SessionLocal
from database.models import (
    Annotation,
    ReviewComment,
    ReviewerApproval,
    AudioFile,
    User,
)

from database.enums import (
    AnnotationState,
    ApprovalStatus,
    AudioStatus,
    UserRole,
)
from utils.logger import logger


def get_db() -> Session:
    return SessionLocal()


# ─────────────────────────────────────────────────────
# Queue helpers
# ─────────────────────────────────────────────────────

def get_submitted_tasks():
    """Return all AudioFiles that are in SUBMITTED state."""
    db = get_db()
    try:
        return (
            db.query(AudioFile)
            .filter(AudioFile.status == AudioStatus.SUBMITTED)
            .order_by(AudioFile.uploaded_at.asc())
            .all()
        )
    finally:
        db.close()


def get_annotation_for_task(audio_id: str):
    """Return the annotation for a given audio task."""
    db = get_db()
    try:
        ann = (
            db.query(Annotation)
            .options(joinedload(Annotation.annotator))
            .filter(
                Annotation.audio_id == audio_id,
                Annotation.state.in_([AnnotationState.SUBMITTED, AnnotationState.APPROVED])
            )
            .first()
        )
        if not ann:
            ann = (
                db.query(Annotation)
                .options(joinedload(Annotation.annotator))
                .filter(Annotation.audio_id == audio_id)
                .order_by(Annotation.updated_at.desc())
                .first()
            )
        return ann
    finally:
        db.close()


def get_all_active_reviewers(db: Session):
    """Return all users with role REVIEWER (active or inactive — see rule)."""
    return (
        db.query(User)
        .filter(User.role == UserRole.REVIEWER)
        .all()
    )


def get_pending_approval_status(annotation_id: str, reviewer_id: str):
    """
    Return whether this reviewer has already approved the current annotation.
    Returns True if already approved, False otherwise.
    """
    db = get_db()
    try:
        existing = (
            db.query(ReviewerApproval)
            .filter(
                ReviewerApproval.annotation_id == annotation_id,
                ReviewerApproval.reviewer_id == reviewer_id,
                ReviewerApproval.status == ApprovalStatus.APPROVED,
            )
            .first()
        )
        return existing is not None
    finally:
        db.close()


# ─────────────────────────────────────────────────────
# Actions
# ─────────────────────────────────────────────────────

def approve(annotation_id: str, reviewer_id: str):
    """
    Record this reviewer's approval. If ALL reviewers have now approved,
    freeze the annotation as APPROVED and mark the audio as REVIEWED.

    Consensus Rule: annotation.state becomes APPROVED only when every
    REVIEWER user in the system has a valid approval record for this
    annotation.
    """
    db = get_db()

    try:
        annotation = (
            db.query(Annotation)
            .filter(Annotation.id == annotation_id)
            .first()
        )

        if not annotation:
            logger.error(f"Annotation {annotation_id} not found.")
            return False

        version = len(annotation.versions)

        # Invalidate any previous approval by this reviewer for this annotation
        # (in case they approved an earlier version and it was returned & resubmitted)
        db.query(ReviewerApproval).filter(
            ReviewerApproval.annotation_id == annotation_id,
            ReviewerApproval.reviewer_id == reviewer_id,
        ).delete()

        approval = ReviewerApproval(
            annotation_id=annotation.id,
            reviewer_id=reviewer_id,
            version_approved=version,
            status=ApprovalStatus.APPROVED,
            is_valid=True,
        )
        db.add(approval)
        db.flush()  # persist so we can query it below

        # ── Consensus Check ──────────────────────────────────────
        all_reviewers = get_all_active_reviewers(db)
        all_reviewer_ids = {r.id for r in all_reviewers}

        approved_reviewer_ids = {
            row.reviewer_id
            for row in db.query(ReviewerApproval).filter(
                ReviewerApproval.annotation_id == annotation_id,
                ReviewerApproval.status == ApprovalStatus.APPROVED,
                ReviewerApproval.is_valid == True,  # noqa: E712
            ).all()
        }

        all_approved = all_reviewer_ids.issubset(approved_reviewer_ids)

        if all_approved:
            annotation.state = AnnotationState.APPROVED

            audio = (
                db.query(AudioFile)
                .filter(AudioFile.id == annotation.audio_id)
                .first()
            )
            audio.status = AudioStatus.COMPLETED

            logger.info(
                f"Annotation {annotation_id} FULLY APPROVED by all reviewers "
                f"({sorted(all_reviewer_ids)}). Audio frozen as COMPLETED."
            )
        else:
            pending = all_reviewer_ids - approved_reviewer_ids
            logger.info(
                f"Annotation {annotation_id}: reviewer {reviewer_id} approved. "
                f"Still waiting on {len(pending)} reviewer(s): {sorted(pending)}"
            )
            # state remains SUBMITTED — still visible to remaining reviewers

        db.commit()

        return True

    except Exception:
        db.rollback()
        logger.exception(f"Failed to approve annotation {annotation_id}")
        return False

    finally:
        db.close()


def validate_review_comment(comment: Optional[str]) -> tuple[bool, str]:
    """
    Validate that a reviewer return comment contains at least 10 actual words.
    Whitespace is normalized before word counting.
    """
    if not comment:
        return False, "Please enter a review comment of at least 10 words before returning this annotation."
    words = [w for w in comment.strip().split() if w]
    if len(words) < 10:
        return False, f"Please enter a review comment of at least 10 words before returning this annotation. (Current word count: {len(words)}/10)"
    return True, ""


def add_comment(annotation_id: str, reviewer_id: str, comment: str):
    """
    Return an annotation to the annotator with a mandatory feedback comment of at least 10 words.
    This immediately unlocks the annotation for editing (RETURNED state).
    All existing valid approval records are invalidated so the next
    submission starts a fresh consensus round.
    """
    is_valid, err_msg = validate_review_comment(comment)
    if not is_valid:
        logger.warning(f"Rejecting return for annotation {annotation_id}: {err_msg}")
        return False, err_msg

    db = get_db()

    try:
        annotation = (
            db.query(Annotation)
            .filter(Annotation.id == annotation_id)
            .first()
        )

        if not annotation:
            return False, "Annotation not found"

        version = len(annotation.versions)

        review = ReviewComment(
            annotation_id=annotation.id,
            reviewer_id=reviewer_id,
            version_commented=version,
            comment=comment,
            is_return_reason=True,
        )
        db.add(review)

        # Invalidate ALL existing approvals — consensus must restart from scratch
        db.query(ReviewerApproval).filter(
            ReviewerApproval.annotation_id == annotation_id,
        ).update({"is_valid": False})

        annotation.state = AnnotationState.RETURNED

        audio = (
            db.query(AudioFile)
            .filter(AudioFile.id == annotation.audio_id)
            .first()
        )
        audio.status = AudioStatus.REWORK_REQUIRED
        audio.assigned_to = annotation.annotator_id
        audio.assigned_at = datetime.utcnow()

        db.commit()

        logger.info(
            f"Annotation {annotation_id} returned by reviewer {reviewer_id}. "
            "All previous approvals invalidated."
        )

        return True, "Annotation returned successfully."

    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to add comment to annotation {annotation_id}: {e}")
        return False, str(e)

    finally:
        db.close()


def get_submitted_annotations():
    """Legacy helper — returns all SUBMITTED annotations."""
    db = get_db()
    try:
        return (
            db.query(Annotation)
            .filter(Annotation.state == AnnotationState.SUBMITTED)
            .all()
        )
    finally:
        db.close()
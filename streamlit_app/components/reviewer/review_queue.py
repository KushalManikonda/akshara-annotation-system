"""
review_queue.py – Phase 6
Renders the reviewer's task queue.

Differences from annotator task_queue:
 - No "Request Next Task" button — reviewers pick from all submitted tasks.
 - Shows who submitted the annotation (annotator username).
 - Shows approval progress (e.g. "1 / 2 reviewers approved").
 - Highlights tasks the current reviewer has already approved.
"""

import streamlit as st
from typing import Optional

from database.database import SessionLocal
from database.models import Annotation, ReviewerApproval, User
from database.enums import ApprovalStatus, UserRole
from utils.audio_utils import get_audio_duration


def _get_review_meta(audio_id: str):
    """
    Return (annotator_username, approved_count, total_reviewer_count)
    for the given audio task.
    """
    db = SessionLocal()
    try:
        annotation = (
            db.query(Annotation)
            .filter(Annotation.audio_id == audio_id)
            .first()
        )
        if not annotation:
            return "—", 0, 0

        annotator_username = (
            annotation.annotator.username
            if annotation.annotator
            else annotation.annotator_id
        )

        # Count valid approvals for this annotation
        approved_count = (
            db.query(ReviewerApproval)
            .filter(
                ReviewerApproval.annotation_id == annotation.id,
                ReviewerApproval.status == ApprovalStatus.APPROVED,
                ReviewerApproval.is_valid == True,  # noqa: E712
            )
            .count()
        )

        total_reviewers = (
            db.query(User)
            .filter(User.role == UserRole.REVIEWER)
            .count()
        )

        return annotator_username, approved_count, total_reviewers

    finally:
        db.close()


def _has_this_reviewer_approved(audio_id: str, reviewer_id: str) -> bool:
    db = SessionLocal()
    try:
        annotation = (
            db.query(Annotation)
            .filter(Annotation.audio_id == audio_id)
            .first()
        )
        if not annotation:
            return False

        return (
            db.query(ReviewerApproval)
            .filter(
                ReviewerApproval.annotation_id == annotation.id,
                ReviewerApproval.reviewer_id == reviewer_id,
                ReviewerApproval.status == ApprovalStatus.APPROVED,
                ReviewerApproval.is_valid == True,  # noqa: E712
            )
            .first()
        ) is not None
    finally:
        db.close()


def render(tasks: list, current_reviewer_id: str) -> Optional[str]:
    """
    Render the reviewer's task queue.

    Args:
        tasks: List of AudioFile objects in SUBMITTED state.
        current_reviewer_id: The logged-in reviewer's user ID.

    Returns:
        The audio ID selected for review, or None.
    """
    st.subheader("📋 Review Queue")
    st.caption(f"{len(tasks)} task(s) awaiting review")

    if not tasks:
        st.info("🎉 No tasks are currently awaiting review.")
        return None

    st.divider()

    selected_id = None

    for task in tasks:
        annotator_username, approved_count, total_reviewers = _get_review_meta(task.id)
        already_approved = _has_this_reviewer_approved(task.id, current_reviewer_id)

        duration = (
            task.duration
            if (task.duration and task.duration > 0)
            else get_audio_duration(task.file_path)
        )

        # Build approval badge
        if total_reviewers > 0:
            approval_badge = f"✅ {approved_count}/{total_reviewers} approved"
        else:
            approval_badge = "No reviewers configured"

        # You-approved indicator
        you_badge = " · 🔵 You approved" if already_approved else ""

        c1, c2 = st.columns([6, 1])

        with c1:
            st.markdown(f"**📄 {task.original_filename}**")
            meta_parts = [task.language]
            if duration > 0:
                mins, secs = divmod(int(duration), 60)
                meta_parts.append(f"{mins}m {secs:02d}s")
            meta_parts.append(f"Submitted by: **{annotator_username}**")
            st.caption(" · ".join(meta_parts))
            st.caption(f"{approval_badge}{you_badge}")

        with c2:
            label = "Review" if not already_approved else "View"
            if st.button(label, key=f"review_task_{task.id}", use_container_width=True):
                selected_id = task.id

        st.divider()

    return selected_id

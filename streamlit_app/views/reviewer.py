"""
views/reviewer.py – Phase 6

Reviewer Workspace.
- Shows all SUBMITTED annotations in a queue with "Submitted by" info.
- Reviewer can open a task, read the annotation, listen to audio.
- They can: Approve (contributes toward consensus) or Return (with comment).
- Annotation is frozen APPROVED only after ALL reviewers approve it.
"""

import streamlit as st

from utils.logout import logout
from utils.logger import logger

from components.annotator.audio_player import render as audio_player
from components.annotator.metadata_panel import render as metadata_panel
from components.annotator.normalized_view import render as normalized_view
from components.annotator.history_panel import render as history_panel
from components.reviewer.review_queue import render as review_queue

from services.reviewer_service import (
    get_submitted_tasks,
    get_annotation_for_task,
    approve,
    add_comment,
    get_pending_approval_status,
)

from services.annotation_service import process_transcript

from database.database import SessionLocal
from database.models import ReviewerApproval, User, Annotation
from database.enums import ApprovalStatus, UserRole


def _get_reviewer_count() -> int:
    db = SessionLocal()
    try:
        return db.query(User).filter(User.role == UserRole.REVIEWER).count()
    finally:
        db.close()


def _get_approved_count(annotation_id: str) -> int:
    db = SessionLocal()
    try:
        return (
            db.query(ReviewerApproval)
            .filter(
                ReviewerApproval.annotation_id == annotation_id,
                ReviewerApproval.status == ApprovalStatus.APPROVED,
                ReviewerApproval.is_valid == True,  # noqa: E712
            )
            .count()
        )
    finally:
        db.close()


def _get_annotator_name(annotation: Annotation) -> str:
    from services.user_service import get_user_by_id
    user = get_user_by_id(annotation.annotator_id)
    if user:
        return user.username
    return annotation.annotator_id


def show():
    user = st.session_state.user

    # ── URL Sync ─────────────────────────────────────────────────────────────
    if "review_task" in st.query_params and "selected_review_task" not in st.session_state:
        st.session_state.selected_review_task = st.query_params["review_task"]
    elif "selected_review_task" not in st.session_state:
        st.session_state.selected_review_task = None
    
    if st.session_state.selected_review_task:
        st.query_params["review_task"] = st.session_state.selected_review_task
    else:
        st.query_params.pop("review_task", None)
    # ─────────────────────────────────────────────────────────────────────────

    col1, col2 = st.columns([8, 1])

    with col1:
        st.title("Reviewer Dashboard")

    with col2:
        if st.button("Logout", use_container_width=True):
            logout()

    tasks = get_submitted_tasks()

    ###########################################################
    # TASK QUEUE
    ###########################################################

    if st.session_state.selected_review_task is None:
        selected_id = review_queue(tasks, user.id)

        if selected_id:
            st.session_state.selected_review_task = selected_id
            st.rerun()

        return

    ###########################################################
    # WORKSPACE
    ###########################################################

    task = next(
        (x for x in tasks if x.id == st.session_state.selected_review_task),
        None,
    )

    if task is None:
        # Task was approved by all and removed from the submitted list
        st.session_state.selected_review_task = None
        st.rerun()

    annotation = get_annotation_for_task(task.id)

    if not annotation:
        st.error(
            "Could not find the submitted annotation for this task. "
            "It may have already been fully approved."
        )
        if st.button("← Back to Queue"):
            st.session_state.selected_review_task = None
            st.rerun()
        return

    # ── Already approved by this reviewer? ──────────────────────────────────
    already_approved = get_pending_approval_status(annotation.id, user.id)

    # ── Top bar ─────────────────────────────────────────────────────────────
    c_back, c_meta = st.columns([2, 7])
    with c_back:
        if st.button("← Back to Queue"):
            st.session_state.selected_review_task = None
            st.rerun()

    with c_meta:
        annotator_name = _get_annotator_name(annotation)
        total_reviewers = _get_reviewer_count()
        approved_count = _get_approved_count(annotation.id)

        submitted_at = (
            annotation.submitted_at.strftime("%d %b %Y, %H:%M")
            if annotation.submitted_at
            else "—"
        )

        st.info(
            f"**Submitted by:** {annotator_name} · **Submitted at:** {submitted_at} · "
            f"**Consensus:** {approved_count}/{total_reviewers} reviewers approved"
            + (" · ✅ You have approved this" if already_approved else "")
        )

    st.divider()
    audio_player(task)
    st.divider()

    left, right = st.columns([3, 2])

    with left:
        metadata_panel(task)
        st.divider()

        st.subheader("Annotator's Verbatim RSML")
        st.text_area(
            "RSML",
            value=annotation.transcript or "",
            height=300,
            disabled=True,
            label_visibility="collapsed",
        )

    result = process_transcript(annotation.transcript or "")

    with right:
        normalized_view(result["ast"])

    st.divider()

    # Version History — reviewers can compare but not restore
    history_panel(
        annotation_id=annotation.id,
        current_text=annotation.transcript or "",
        allow_restore=False,
    )

    st.divider()

    ###########################################################
    # REVIEW DECISION PANEL
    ###########################################################

    st.subheader("Review Decision")

    col_feedback, col_actions = st.columns([3, 2])

    with col_feedback:
        feedback = st.text_area(
            "Feedback Comment",
            placeholder="Explain what needs fixing if returning the task...",
            height=120,
            disabled=already_approved,
        )

    with col_actions:
        st.write("")  # spacing

        if already_approved:
            st.success("✅ You have already approved this annotation.")
            st.caption(
                f"Waiting for {total_reviewers - approved_count} more reviewer(s)."
            )
        else:
            if st.button(
                "✅ Approve Annotation",
                use_container_width=True,
                type="primary",
            ):
                if approve(annotation.id, user.id):
                    # Recompute after approval
                    new_approved = _get_approved_count(annotation.id)
                    if new_approved >= total_reviewers:
                        st.success("🎉 All reviewers approved! Annotation is now frozen.")
                    else:
                        remaining = total_reviewers - new_approved
                        st.success(
                            f"✅ Your approval recorded. "
                            f"Waiting for {remaining} more reviewer(s)."
                        )
                    logger.info(
                        f"Reviewer {user.id} approved annotation {annotation.id}"
                    )
                    st.session_state.selected_review_task = None
                    st.rerun()
                else:
                    st.error("Failed to record approval. Please try again.")

        st.write("")

        if not already_approved:
            if st.button("❌ Return to Annotator", use_container_width=True):
                if not feedback.strip():
                    st.warning(
                        "⚠️ Please write a feedback comment before returning the task."
                    )
                else:
                    if add_comment(annotation.id, user.id, feedback):
                        st.success("Task returned to annotator with your feedback.")
                        logger.info(
                            f"Reviewer {user.id} returned annotation {annotation.id}"
                        )
                        st.session_state.selected_review_task = None
                        st.rerun()
                    else:
                        st.error("Failed to return task. Please try again.")
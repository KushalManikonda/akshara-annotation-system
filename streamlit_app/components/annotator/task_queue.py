"""
task_queue.py – Phase 5.1 (updated Phase 6)
Renders the annotator's task queue and the "Request Next Task" button.
This component handles the task-selection UI only; business logic
lives in services/task_service.py.
"""

import streamlit as st

from database.enums import AudioStatus
from database.database import SessionLocal
from database.models import Annotation, ReviewComment
from database.enums import AnnotationState
from typing import Optional
from utils.audio_utils import get_audio_duration


def _get_annotation_state(audio_id: str, annotator_id: str):
    """Return (AnnotationState, latest_return_comment) for a task."""
    db = SessionLocal()
    try:
        annotation = (
            db.query(Annotation)
            .filter(
                Annotation.audio_id == audio_id,
                Annotation.annotator_id == annotator_id,
            )
            .first()
        )
        if not annotation:
            return None, None

        # Find the most recent return reason comment
        comment = (
            db.query(ReviewComment)
            .filter(
                ReviewComment.annotation_id == annotation.id,
                ReviewComment.is_return_reason == True,  # noqa: E712
            )
            .order_by(ReviewComment.created_at.desc())
            .first()
        )

        return annotation.state, (comment.comment if comment else None)
    finally:
        db.close()


def render(tasks: list, on_request_task) -> Optional[str]:
    """
    Render the task queue panel.

    Args:
        tasks: List of AudioFile objects assigned to the annotator.
        on_request_task: Callable with no arguments; called when the
                         annotator clicks "Request Next Task".

    Returns:
        The audio ID selected by the annotator, or None.
    """
    st.subheader("📋 My Task Queue")

    # Status badge mapping (AudioFile.status → icon)
    STATUS_ICONS = {
        AudioStatus.ASSIGNED: "🔵",
        AudioStatus.IN_PROGRESS: "🟡",
        AudioStatus.SUBMITTED: "✅",
    }

    col_req, col_info = st.columns([2, 3])

    with col_req:
        if on_request_task and st.button(
            "⚡ Request Next Task",
            use_container_width=True,
            type="primary",
        ):
            on_request_task()

    with col_info:
        st.caption(f"{len(tasks)} task(s) in queue")

    if not tasks:
        st.info("No tasks assigned yet. Click **Request Next Task** to get started.")
        return None

    st.divider()

    # We need the current user to look up annotation states
    current_user = st.session_state.get("user")
    annotator_id = current_user.id if current_user else None

    selected_id = None

    for task in tasks:
        icon = STATUS_ICONS.get(task.status, "⚪")
        status_label = task.status.value.replace("_", " ").title()

        # Look up annotation state to detect RETURNED tasks
        ann_state, return_comment = (
            _get_annotation_state(task.id, annotator_id)
            if annotator_id
            else (None, None)
        )

        is_returned = ann_state == AnnotationState.RETURNED

        # Override icon and label for returned tasks
        if is_returned:
            icon = "🔴"
            status_label = "Returned for Correction"

        duration = (
            task.duration
            if (task.duration and task.duration > 0)
            else get_audio_duration(task.file_path)
        )

        c1, c2 = st.columns([6, 1])

        with c1:
            st.markdown(f"**{icon} {task.original_filename}**")
            meta_parts = [task.language, status_label]
            if duration > 0:
                mins, secs = divmod(int(duration), 60)
                meta_parts.append(f"{mins}m {secs:02d}s")
            st.caption(" · ".join(meta_parts))

            # Show reviewer's comment if returned
            if is_returned and return_comment:
                st.warning(f"💬 Reviewer feedback: *{return_comment}*")

        with c2:
            if st.button(
                "Open",
                key=f"open_task_{task.id}",
                use_container_width=True,
            ):
                selected_id = task.id

        st.divider()

    return selected_id

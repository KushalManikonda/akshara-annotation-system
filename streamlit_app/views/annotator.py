import streamlit as st

from utils.logout import logout
from utils.logger import logger

from components.annotator.wavesurfer_editor import render as wavesurfer_editor
from components.annotator.navigation import render as navigation
from components.annotator.tag_reference import render as tag_reference
from components.annotator.footer import render as footer
from components.annotator.task_queue import render as task_queue
from components.annotator.history_panel import render as history_panel

from services.task_service import (
    reserve_next_task,
    get_annotator_tasks,
)

from services.annotation_service import (
    get_annotation,
    save_annotation,
    submit_annotation,
    process_transcript,
    format_transcript,
)


def show():

    user = st.session_state.user

    # ── URL Sync ─────────────────────────────────────────────────────────────
    if "task" in st.query_params and "selected_task" not in st.session_state:
        st.session_state.selected_task = st.query_params["task"]
    elif "selected_task" not in st.session_state:
        st.session_state.selected_task = None
    
    if st.session_state.selected_task:
        st.query_params["task"] = st.session_state.selected_task
    else:
        st.query_params.pop("task", None)
    # ─────────────────────────────────────────────────────────────────────────

    col1, col2 = st.columns([8, 1])

    with col1:
        st.title("Akshara RSML Studio")

    with col2:
        if st.button("Logout", use_container_width=True):
            logout()

    # Always fetch fresh task list via task_service (includes ASSIGNED + IN_PROGRESS + SUBMITTED)
    tasks = get_annotator_tasks(user.id)

    ###########################################################
    # TASK QUEUE
    ###########################################################

    if st.session_state.selected_task is None:

        def _on_request_task():
            reserved = reserve_next_task(user.id)
            if reserved:
                st.session_state.selected_task = reserved.id
                st.toast(f"Task reserved: {reserved.original_filename}", icon="✅")
                logger.info(
                    f"Annotator {user.id} reserved task {reserved.id}"
                )
            else:
                st.toast("No tasks available right now.", icon="ℹ️")

        selected_id = task_queue(tasks, _on_request_task)

        if selected_id:
            st.session_state.selected_task = selected_id
            st.rerun()

        return

    ###########################################################
    # WORKSPACE
    ###########################################################

    task = next(
        (x for x in tasks if x.id == st.session_state.selected_task),
        None,
    )

    if task is None:
        st.session_state.selected_task = None
        st.rerun()

    annotation = get_annotation(task.id, user.id)

    # Lock if SUBMITTED (under review) or APPROVED (frozen).
    # RETURNED tasks stay editable so annotator can fix and resubmit.
    from database.enums import AnnotationState
    is_read_only = annotation.state in [AnnotationState.SUBMITTED, AnnotationState.APPROVED]

    # Show return feedback banner
    if annotation.state == AnnotationState.RETURNED:
        from database.database import SessionLocal
        from database.models import ReviewComment
        db = SessionLocal()
        try:
            rc = (
                db.query(ReviewComment)
                .filter(
                    ReviewComment.annotation_id == annotation.id,
                    ReviewComment.is_return_reason == True,  # noqa: E712
                )
                .order_by(ReviewComment.created_at.desc())
                .first()
            )
            if rc:
                st.warning(
                    f"🔴 **Returned for correction** · Reviewer feedback: *{rc.comment}*",
                    icon="💬"
                )
        finally:
            db.close()

    c_back, c_empty = st.columns([2, 8])
    with c_back:
        if st.button("← Back to Queue"):
            st.session_state.selected_task = None
            st.rerun()

    if is_read_only:
        st.info("🔒 This annotation has been submitted for review and is currently locked. It is read-only unless returned by a reviewer.", icon="🔒")
    else:
        has_errors = False
        save, abandon_task, submit = footer(has_errors)

        if save:
            ok = save_annotation(
                annotation.id,
                annotation.transcript or "",
                annotation.rsml_content or "",
            )
            if ok:
                st.success("Draft saved.")
                logger.info(f"Draft saved for annotation {annotation.id}")
            else:
                st.error("Failed to save draft. Please try again.")

        if abandon_task:
            from services.task_service import release_task
            if release_task(task.id, user.id):
                st.success("Task released back to the queue.")
                st.session_state.selected_task = None
                st.rerun()
            else:
                st.error("Failed to release task.")

        if submit:
            ok = submit_annotation(annotation.id)
            if ok:
                st.success("Annotation submitted successfully.")
                logger.info(f"Annotation {annotation.id} submitted by {user.id}")
                st.session_state.selected_task = None
                st.rerun()
            else:
                st.error("Submission failed. Please try again.")

    ws_result = wavesurfer_editor(task, annotation, is_read_only)

    if ws_result and isinstance(ws_result, dict):
        action = ws_result.get("action")
        if action in ["prev_task", "next_task"]:
            current_idx = next((i for i, t in enumerate(tasks) if t.id == task.id), -1)
            if action == "prev_task" and current_idx > 0:
                st.session_state.selected_task = tasks[current_idx - 1].id
                st.rerun()
            elif action == "next_task" and current_idx < len(tasks) - 1:
                st.session_state.selected_task = tasks[current_idx + 1].id
                st.rerun()
            else:
                st.toast("No more tasks in that direction.", icon="ℹ️")

    st.divider()

    st.divider()

    st.divider()

    st.divider()

    tag_reference()

    st.divider()

    # Version History (annotators can also restore)
    restored = history_panel(
        annotation_id=annotation.id,
        current_text=annotation.transcript or "",
        allow_restore=(not is_read_only),
    )
    if restored is not None:
        # Push the restored text into session_state so the editor reflects it
        ok = save_annotation(annotation.id, restored, annotation.rsml_content or "")
        if ok:
            st.success("✅ Draft restored to selected version.")
            st.rerun()
        else:
            st.error("Failed to restore version.")

    # Removed footer from here as it's now placed above
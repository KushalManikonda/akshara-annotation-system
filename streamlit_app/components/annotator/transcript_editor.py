import streamlit as st


def render(annotation, task, is_read_only: bool = False):
    """
    Render the RSML transcript text area.
    Uses session_state + on_change for continuous (blur-triggered) validation.
    """

    # Session state key scoped per annotation so different tasks don't bleed
    sk = f"transcript_{annotation.id}"

    # Initialise the session state value on first load
    if sk not in st.session_state:
        default_value = annotation.transcript
        if not default_value and task.original_transcript:
            default_value = task.original_transcript
        st.session_state[sk] = default_value or ""

    def _on_change():
        # on_change fires when the widget loses focus
        new_val = st.session_state[sk]
        if not is_read_only:
            from services.annotation_service import save_annotation
            from utils.logger import logger
            ok = save_annotation(annotation.id, new_val, annotation.rsml_content or "")
            if ok:
                logger.info(f"Auto-saved draft for annotation {annotation.id}")

    st.text_area(
        "RSML Transcript",
        key=sk,
        height=300,
        placeholder="Enter RSML annotated transcript here...",
        on_change=_on_change,
        disabled=is_read_only
    )

    return st.session_state[sk]
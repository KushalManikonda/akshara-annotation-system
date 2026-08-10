import streamlit as st


def render(has_errors: bool):

    c1, c2, c3 = st.columns(3)

    save = c1.button(
        "💾 Save Draft",
        use_container_width=True
    )

    abandon_task = c2.button(
        "🗑️ Abandon Task",
        use_container_width=True,
        help="Release this task back to the queue (deletes draft)"
    )

    submit = c3.button(
        "📤 Submit",
        use_container_width=True,
        disabled=has_errors,
        help="Fix all validation errors before submitting" if has_errors else "Submit annotation for review"
    )

    return save, abandon_task, submit
import streamlit as st


def render(messages):

    st.subheader("Validation")

    if not messages:
        st.success("✅ No validation errors. RSML is valid!")
        return

    errors = [m for m in messages if m.level == "ERROR"]
    warnings = [m for m in messages if m.level == "WARNING"]

    if errors:
        st.error(f"❌ **{len(errors)} Error(s) found**")
        for error in errors:
            st.markdown(f"- {error.message}")

    if warnings:
        st.warning(f"⚠️ **{len(warnings)} Warning(s) found**")
        for warning in warnings:
            st.markdown(f"- {warning.message}")
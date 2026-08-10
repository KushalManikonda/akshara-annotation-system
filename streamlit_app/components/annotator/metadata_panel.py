import streamlit as st
import json

def render(task):
    """
    Displays the contextual metadata (Original Transcript & Translation)
    for the annotator to reference while annotating.
    """
    st.subheader("📄 Context")
    
    with st.expander("Original Transcript", expanded=True):
        st.write(task.original_transcript or "*(No original transcript available)*")
        
    with st.expander("English Translation", expanded=True):
        st.write(task.english_translation or "*(No english translation available)*")
        
    if task.metadata_json:
        try:
            extra = json.loads(task.metadata_json)
            if extra:
                with st.expander("Additional Metadata", expanded=False):
                    st.json(extra)
        except Exception:
            pass

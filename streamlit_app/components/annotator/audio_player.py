import streamlit as st
import os
from utils.audio_utils import get_audio_duration


def render(audio):

    st.subheader("🎧 Audio Player")

    if hasattr(audio, 'audio_url') and audio.audio_url:
        st.audio(audio.audio_url)
    elif os.path.exists(audio.file_path):
        st.audio(audio.file_path)
    else:
        st.warning(f"⚠️ Audio file not found locally and no URL available: {audio.file_path}")

    # Compute duration live — the DB column is stored as 0.0 for legacy uploads
    duration = audio.duration if (audio.duration and audio.duration > 0) else (get_audio_duration(audio.file_path) if os.path.exists(audio.file_path) else 0.0)

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.caption(f"Language : {audio.language}")

    with c2:
        st.caption(f"Status : {audio.status.value}")

    with c3:
        if duration > 0:
            mins, secs = divmod(int(duration), 60)
            st.caption(f"Duration : {mins}m {secs:02d}s")
        else:
            st.caption("Duration : —")

    with c4:
        st.caption(audio.original_filename)
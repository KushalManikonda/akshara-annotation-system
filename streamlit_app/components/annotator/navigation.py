import streamlit as st


def render():

    c1, c2, c3 = st.columns([1,6,1])

    with c1:

        previous = st.button(
            "⬅ Previous",
            use_container_width=True
        )

    with c3:

        next_audio = st.button(
            "Next ➡",
            use_container_width=True
        )

    return previous, next_audio
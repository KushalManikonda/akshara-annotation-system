import streamlit as st


def render():

    st.subheader("RSML Toolbar")

    c1,c2,c3,c4,c5,c6 = st.columns(6)

    with c1:
        st.button("@umm")

    with c2:
        st.button("@silence")

    with c3:
        st.button("@repair")

    with c4:
        st.button("#NER")

    with c5:
        st.button("!LANG")

    with c6:
        st.button("@laugh")
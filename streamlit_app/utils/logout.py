from datetime import datetime

import streamlit as st

from database.database import SessionLocal
from database.models import User


def logout():

    if "user" in st.session_state:

        db = SessionLocal()

        try:

            user = (
                db.query(User)
                .filter(User.id == st.session_state.user.id)
                .first()
            )

            if user:
                user.last_seen = datetime.utcnow()
                db.commit()

        except Exception:
            db.rollback()

        finally:
            db.close()

    raw_token = st.session_state.get("session_token")
    if raw_token:
        from services.session_service import destroy_session
        destroy_session(raw_token)

    keys = list(st.session_state.keys())

    for key in keys:
        del st.session_state[key]

    st.session_state.pending_logout_cookie = True
    st.rerun()
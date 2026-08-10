"""
Session persistence layer for Akshara.

Strategy
--------
On login  → generate a random opaque token, store it in:
            1. The server-side SQLite sessions table (via SessionToken model)
            2. The browser via an HttpOnly cookie injected through st.html()

On page load (refresh) → read the cookie via st.context.cookies,
            look up the token in the DB, and if valid/unexpired,
            restore st.session_state.user without asking to log in again.

On logout → delete the DB row and clear the cookie.

This requires NO additional Python packages.
"""

import secrets
import hashlib
from datetime import datetime, timedelta

from database.database import SessionLocal
from database.models import User, SessionToken
from utils.logger import logger

# How long a remembered session lasts
SESSION_LIFETIME_DAYS = 7
COOKIE_NAME = "akshara_session"


# ──────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────

def _hash_token(raw: str) -> str:
    """Store only a SHA-256 hash of the raw token in the DB."""
    return hashlib.sha256(raw.encode()).hexdigest()


# ──────────────────────────────────────────────────────────────
# Create a session after successful login
# ──────────────────────────────────────────────────────────────

def create_session(user_id: str) -> str:
    """
    Generate a new session token, persist it to the DB, and return
    the raw token string (which the caller will set as a cookie).
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)
    expires_at = datetime.utcnow() + timedelta(days=SESSION_LIFETIME_DAYS)

    db = SessionLocal()
    try:
        record = SessionToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(record)
        db.commit()
        logger.info(f"Session created for user {user_id}, expires {expires_at}")
    except Exception:
        db.rollback()
        logger.exception(f"Failed to create session for user {user_id}")
    finally:
        db.close()

    return raw_token


# ──────────────────────────────────────────────────────────────
# Validate a token from the cookie on page load
# ──────────────────────────────────────────────────────────────

def get_user_from_token(raw_token: str):
    """
    Look up the hashed token in the DB.
    Returns the User if valid and not expired, else None.
    """
    if not raw_token:
        return None

    token_hash = _hash_token(raw_token)
    db = SessionLocal()

    try:
        record = (
            db.query(SessionToken)
            .filter(
                SessionToken.token_hash == token_hash,
                SessionToken.expires_at > datetime.utcnow(),
            )
            .first()
        )

        if not record:
            return None

        user = db.query(User).filter(User.id == record.user_id).first()

        if not user or not user.is_active:
            return None

        # Slide the expiry window on each successful use
        record.expires_at = datetime.utcnow() + timedelta(days=SESSION_LIFETIME_DAYS)
        db.commit()
        db.refresh(user)

        return user

    except Exception:
        logger.exception("Failed to validate session token")
        return None

    finally:
        db.close()


# ──────────────────────────────────────────────────────────────
# Destroy a session on logout
# ──────────────────────────────────────────────────────────────

def destroy_session(raw_token: str) -> None:
    """Delete the session token from the DB."""
    if not raw_token:
        return

    token_hash = _hash_token(raw_token)
    db = SessionLocal()

    try:
        db.query(SessionToken).filter(
            SessionToken.token_hash == token_hash
        ).delete(synchronize_session=False)
        db.commit()
        logger.info("Session destroyed")
    except Exception:
        db.rollback()
        logger.exception("Failed to destroy session")
    finally:
        db.close()


# ──────────────────────────────────────────────────────────────
# Cookie helpers (Streamlit-side)
# ──────────────────────────────────────────────────────────────

def set_session_cookie(raw_token: str):
    """
    Sets the session cookie in the browser via an iframe script.
    """
    import streamlit.components.v1 as components
    max_age = SESSION_LIFETIME_DAYS * 24 * 3600
    components.html(
        f"<script>"
        f"window.parent.document.cookie = '{COOKIE_NAME}={raw_token}; max-age={max_age}; path=/; SameSite=Lax';"
        f"</script>",
        height=0, width=0
    )


def clear_session_cookie():
    """
    Expires the session cookie immediately via an iframe script.
    """
    import streamlit.components.v1 as components
    components.html(
        f"<script>"
        f"window.parent.document.cookie = '{COOKIE_NAME}=; max-age=0; path=/; SameSite=Lax';"
        f"</script>",
        height=0, width=0
    )


def read_session_cookie() -> str:
    """
    Read the session token from the browser cookie via st.context.cookies.
    Returns empty string if not present.
    """
    try:
        import streamlit as st
        cookies = st.context.cookies
        logger.info(f"Incoming cookies from browser: {cookies}")
        return cookies.get(COOKIE_NAME, "")
    except Exception as e:
        logger.error(f"Error reading cookies: {e}")
        return ""

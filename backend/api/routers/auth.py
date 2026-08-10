"""
backend/api/routers/auth.py
----------------------------
Authentication endpoints.

POST /auth/login    — Validates credentials, issues access token (JSON) +
                      refresh token (HttpOnly cookie), persists token hash in DB.
POST /auth/refresh  — Reads the HttpOnly refresh cookie, verifies it against DB,
                      returns a new access token and rotates the refresh token.
POST /auth/logout   — Deletes the session from DB and clears the cookie.
"""

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.dependencies import get_db
from backend.core.security import (
    create_access_token,
    create_refresh_token,
    hash_token,
    verify_password,
)
from backend.services.user_service import get_user_by_username
from backend.database.models import SessionToken

router = APIRouter(prefix="/auth", tags=["auth"])

# ── Cookie config ─────────────────────────────────────────────────────────────

_COOKIE_NAME = "refresh_token"
_COOKIE_MAX_AGE = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60  # seconds


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    is_production = settings.ENVIRONMENT == "production"
    response.set_cookie(
        key=_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=is_production,   # True in production (HTTPS), False in dev (HTTP)
        samesite="lax",         # Lax is safe for same-origin proxied requests (Vercel → Render)
        max_age=_COOKIE_MAX_AGE,
        path="/api/auth",       # Scoped — cookie only sent to auth endpoints
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=_COOKIE_NAME,
        path="/api/auth",
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create_and_persist_refresh_token(user_id: str, db: Session) -> str:
    """Generate a new refresh token, hash it, store in DB, return the raw value."""
    raw_token = create_refresh_token(data={"sub": user_id})
    token_hash = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    session = SessionToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(session)
    db.commit()
    return raw_token


def _revoke_refresh_token(token_hash: str, db: Session) -> None:
    """Delete a session row by its hash (logout / rotation)."""
    db.query(SessionToken).filter(SessionToken.token_hash == token_hash).delete()
    db.commit()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/login")
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Exchange credentials for tokens.
    Returns access_token in JSON (short-lived, 15 min).
    Sets an HttpOnly refresh_token cookie (long-lived, 7 days).
    """
    user = get_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user account")

    user.last_login = datetime.utcnow()
    user.last_seen = datetime.utcnow()
    db.commit()

    access_token = create_access_token(
        data={"sub": user.id, "role": user.role.value},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    raw_refresh = _create_and_persist_refresh_token(user.id, db)
    _set_refresh_cookie(response, raw_refresh)

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/refresh")
def refresh_token_endpoint(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: str = Cookie(default=None),
):
    """
    Issue a new access token from the HttpOnly refresh cookie.
    Rotates the refresh token on every call (old revoked, new issued).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session expired — please log in again",
    )

    if not refresh_token:
        raise credentials_exception

    token_hash = hash_token(refresh_token)
    session = db.query(SessionToken).filter(SessionToken.token_hash == token_hash).first()

    if not session:
        raise credentials_exception

    # Check expiry (handle naive UTC datetimes stored by older code)
    now = datetime.now(timezone.utc)
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if now > expires_at:
        _revoke_refresh_token(token_hash, db)
        _clear_refresh_cookie(response)
        raise credentials_exception

    user_id = session.user_id

    # Rotate tokens
    _revoke_refresh_token(token_hash, db)
    raw_refresh_new = _create_and_persist_refresh_token(user_id, db)

    access_token = create_access_token(
        data={"sub": user_id},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    _set_refresh_cookie(response, raw_refresh_new)

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
def logout(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: str = Cookie(default=None),
):
    """
    Revoke the refresh session server-side and clear the cookie.
    Safe to call even if the cookie is already missing.
    """
    if refresh_token:
        _revoke_refresh_token(hash_token(refresh_token), db)
    _clear_refresh_cookie(response)
    return {"message": "Logged out successfully"}


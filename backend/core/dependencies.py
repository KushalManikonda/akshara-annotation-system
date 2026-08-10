"""
backend/core/dependencies.py
-----------------------------
FastAPI dependency injection helpers.

These are used as Depends() in route functions to:
- Extract the current user from the JWT
- Enforce role-based access control
- Provide a DB session

Usage:
    @router.get("/admin/users")
    async def get_users(user: User = Depends(require_role(UserRole.ADMIN))):
        ...
"""

from typing import List

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.core.config import settings
from backend.core.security import decode_token

# We import the SQLAlchemy session and models from the shared location
# (which will be the streamlit_app/ folder during Phase 1-3, then
# migrated to backend/database/ in later phases)
import sys
import os

# Add the streamlit_app path so we can reuse the existing services
_STREAMLIT_APP = os.path.join(
    os.path.dirname(__file__),  # backend/core/
    "..", "..",                  # project root
    "streamlit_app"
)
if _STREAMLIT_APP not in sys.path:
    sys.path.insert(0, _STREAMLIT_APP)

from database.database import SessionLocal
from database.models import User
from database.enums import UserRole
from sqlalchemy.orm import Session

bearer_scheme = HTTPBearer(auto_error=False)


def get_db():
    """Dependency: yields a SQLAlchemy session, closes it on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency: Extracts and validates the JWT from the Authorization header.
    Returns the authenticated User object.
    Raises 401 if missing, invalid, or expired.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_type = payload.get("type")
    if token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wrong token type — use access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing subject",
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return user


def require_role(*allowed_roles: UserRole):
    """
    Dependency factory: Returns a dependency that requires the user to have
    one of the specified roles.

    Usage:
        Depends(require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))

    IMPORTANT: Authorization is ALWAYS enforced server-side here.
    Never trust frontend-provided role claims.
    """
    def _check_role(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {[r.value for r in allowed_roles]}",
            )
        return current_user
    return _check_role

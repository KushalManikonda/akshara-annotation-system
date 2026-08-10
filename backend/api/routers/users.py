from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from backend.core.dependencies import get_current_user
from backend.core.security import verify_password, hash_password
from backend.schemas.user import UserResponse, UserCreate, UserUpdate, ChangePassword, AdminSetPassword
from database.models import User
from database.enums import UserRole
from database.database import SessionLocal
from services.user_service import (
    get_all_users, get_user_by_id, create_user,
    update_user, delete_user, activate_user, deactivate_user
)

router = APIRouter(prefix="/users", tags=["users"])


def _require_admin(current_user: User):
    role_val = current_user.role.value if hasattr(current_user.role, 'value') else current_user.role
    if role_val not in ["ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")


def _to_user_response(user: User) -> UserResponse:
    activity_status = "Never Logged In"
    if user.last_login:
        if user.last_seen and (datetime.utcnow() - user.last_seen).total_seconds() <= 900:
            activity_status = "Online"
        else:
            activity_status = "Offline"

    role_str = user.role.value if hasattr(user.role, 'value') else str(user.role)
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=role_str,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login=user.last_login,
        last_seen=user.last_seen,
        activity_status=activity_status
    )


@router.post("/add", response_model=UserResponse)
def create_new_user(payload: UserCreate, current_user: User = Depends(get_current_user)):
    """Create a new user. Admin only."""
    _require_admin(current_user)
    try:
        role_enum = UserRole(payload.role)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role")

    new_user = create_user(
        username=payload.username,
        email=payload.email,
        password=payload.password,
        role=role_enum
    )
    if not new_user:
        raise HTTPException(status_code=400, detail="Username or Email already exists")
    return _to_user_response(new_user)


@router.get("", response_model=List[UserResponse])
def read_users(current_user: User = Depends(get_current_user)):
    """Get all users."""
    return [_to_user_response(u) for u in get_all_users()]


@router.get("/me", response_model=UserResponse)
def read_user_me(current_user: User = Depends(get_current_user)):
    """Get current logged in user."""
    return _to_user_response(current_user)


@router.put("/{user_id}", response_model=UserResponse)
def edit_user(user_id: str, payload: UserUpdate, current_user: User = Depends(get_current_user)):
    """Edit a user's username, email, role, and active status. Admin only."""
    _require_admin(current_user)
    try:
        role_enum = UserRole(payload.role)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.username = payload.username
        user.email = payload.email
        user.role = role_enum
        user.is_active = payload.is_active
        db.commit()
        db.refresh(user)
        return _to_user_response(user)
    finally:
        db.close()


@router.delete("/{user_id}")
def remove_user(user_id: str, current_user: User = Depends(get_current_user)):
    """Delete a user. Admin only. Cannot delete yourself or the last admin."""
    _require_admin(current_user)
    success, msg = delete_user(user_id, current_user.id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}


@router.post("/me/change-password")
def change_own_password(payload: ChangePassword, current_user: User = Depends(get_current_user)):
    """Change the currently logged-in user's password."""
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        user.password_hash = hash_password(payload.new_password)
        db.commit()
    finally:
        db.close()
    return {"message": "Password changed successfully"}


@router.post("/{user_id}/set-password")
def admin_set_password(user_id: str, payload: AdminSetPassword, current_user: User = Depends(get_current_user)):
    """Admin sets a new password for any user."""
    _require_admin(current_user)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.password_hash = hash_password(payload.new_password)
        db.commit()
    finally:
        db.close()
    return {"message": "Password updated successfully"}


@router.get("/{user_id}", response_model=UserResponse)
def read_user(user_id: str, current_user: User = Depends(get_current_user)):
    """Get specific user by ID."""
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _to_user_response(user)

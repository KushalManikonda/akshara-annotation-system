from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    role: str
    is_active: bool

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    role: str
    is_active: bool

class ChangePassword(BaseModel):
    current_password: str
    new_password: str

class AdminSetPassword(BaseModel):
    new_password: str

class UserResponse(UserBase):
    id: str
    created_at: datetime
    last_login: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    activity_status: Optional[str] = "Never Logged In"

    class Config:
        from_attributes = True

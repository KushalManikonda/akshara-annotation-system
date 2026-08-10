from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.core.dependencies import get_db, require_role
from backend.database.models import User, SystemSettings
from backend.database.enums import UserRole
import uuid

router = APIRouter(prefix="/settings", tags=["settings"])

class MaintenanceModeUpdate(BaseModel):
    maintenance_mode: bool

@router.get("/maintenance")
def get_maintenance_mode(db: Session = Depends(get_db)):
    settings_record = db.query(SystemSettings).first()
    if not settings_record:
        return {"maintenance_mode": False}
    return {"maintenance_mode": settings_record.maintenance_mode}

@router.post("/maintenance")
def set_maintenance_mode(
    payload: MaintenanceModeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    settings_record = db.query(SystemSettings).first()
    if not settings_record:
        settings_record = SystemSettings(id=str(uuid.uuid4()), maintenance_mode=payload.maintenance_mode)
        db.add(settings_record)
    else:
        settings_record.maintenance_mode = payload.maintenance_mode
    db.commit()
    return {"maintenance_mode": settings_record.maintenance_mode}

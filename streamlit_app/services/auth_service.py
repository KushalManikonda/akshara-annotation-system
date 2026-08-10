from sqlalchemy.orm import Session

from database.models import User
from database.database import SessionLocal
from utils.security import verify_password
from utils.logger import logger

from datetime import datetime


def update_last_seen(user_id):

    db = SessionLocal()

    try:

        user = db.query(User).filter(User.id == user_id).first()

        if user:
            user.last_seen = datetime.utcnow()
            db.commit()

    except Exception:
        db.rollback()
        logger.exception(f"Failed to update last seen for {user_id}")

    finally:
        db.close()
        
def get_db() -> Session:
    return SessionLocal()


def get_user_by_username(username: str):
    db = get_db()

    try:
        return (
            db.query(User)
            .filter(User.username == username)
            .first()
        )

    finally:
        db.close()


def authenticate_user(username: str, password: str):

    db = get_db()

    try:

        user = (
            db.query(User)
            .filter(User.username == username)
            .first()
        )

        if not user:
            return None

        if not user.is_active:
            return None

        if not verify_password(password, user.password_hash):
            return None

        now = datetime.utcnow()

        user.last_login = now
        user.last_seen = now

        db.commit()
        db.refresh(user)

        return user

    except Exception:
        db.rollback()
        logger.exception(f"Authentication failed for {username}")
        return None

    finally:
        db.close()
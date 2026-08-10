from backend.database.database import SessionLocal
from backend.database.models import User
from backend.database.enums import UserRole
from backend.utils.security import hash_password
from backend.utils.logger import logger

db = SessionLocal()

try:
    admin = db.query(User).filter(User.username == "admin").first()

    if admin:
        logger.info("Admin already exists.")
        db.close()
        exit()

    admin = User(
        username="admin",
        email="admin@akshara.com",
        password_hash=hash_password("admin123"),
        role=UserRole.ADMIN
    )

    db.add(admin)
    db.commit()
    logger.info("Admin created successfully.")

except Exception:
    db.rollback()
    logger.exception("Failed to create admin")

finally:
    db.close()

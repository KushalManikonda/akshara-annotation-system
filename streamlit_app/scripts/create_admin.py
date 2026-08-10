from database.database import SessionLocal
from database.models import User
from database.enums import UserRole
from utils.security import hash_password
from utils.logger import logger

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

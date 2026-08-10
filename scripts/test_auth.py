from database.database import SessionLocal
from database.models import User
from utils.security import verify_password

db = SessionLocal()

users = db.query(User).all()

print(f"Total users: {len(users)}")

for user in users:
    print("-" * 40)
    print("Username :", user.username)
    print("Email    :", user.email)
    print("Active   :", user.is_active)
    print("Role     :", user.role)
    print("Hash     :", user.password_hash)
    print("Verify   :", verify_password("admin123", user.password_hash))

db.close()
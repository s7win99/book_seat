from database import SessionLocal, engine, Base
import models
from auth import hash_password

Base.metadata.create_all(bind=engine)

# Migration: add bonus column if missing
import sqlite3
db_path = str(engine.url).replace("sqlite:///", "")
try:
    conn = sqlite3.connect(db_path)
    conn.execute("ALTER TABLE attendance_records ADD COLUMN bonus INTEGER DEFAULT 0")
    conn.commit()
    print("Migration: added bonus column to attendance_records")
except sqlite3.OperationalError:
    pass  # column already exists
finally:
    conn.close()

db = SessionLocal()

if not db.query(models.User).filter(models.User.username == "admin").first():
    admin = models.User(
        username="admin",
        name="Admin",
        password_hash=hash_password("admin123"),
        role="superadmin",
    )
    db.add(admin)
    db.commit()
    print("Admin user created: admin / admin123 (superadmin)")
else:
    existing = db.query(models.User).filter(models.User.username == "admin").first()
    if existing.role != "superadmin":
        existing.role = "superadmin"
        db.commit()
        print("Admin user upgraded to superadmin")
    else:
        print("Admin user already exists (superadmin)")

db.close()

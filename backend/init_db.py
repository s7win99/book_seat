from database import SessionLocal, engine, Base
import models
from auth import hash_password

Base.metadata.create_all(bind=engine)

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

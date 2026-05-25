import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lab_attendance.db")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
COOLDOWN_MINUTES = 1
VALID_ATTENDANCE_MINUTES = 180
WEEKEND_TOTAL_MINUTES = 540

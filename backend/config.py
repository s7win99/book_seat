import os
import secrets
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lab_attendance.db")
_default_secret = secrets.token_urlsafe(32)
SECRET_KEY = os.getenv("SECRET_KEY", _default_secret)
if not os.getenv("SECRET_KEY"):
    import warnings
    warnings.warn("SECRET_KEY not set, using random key (tokens will invalidate on restart)")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
COOLDOWN_MINUTES = 1
VALID_ATTENDANCE_MINUTES = 180
WEEKEND_TOTAL_MINUTES = 540
BASE_URL = os.getenv("BASE_URL", "http://localhost:5173")

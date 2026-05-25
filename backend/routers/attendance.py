from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from models import User, AttendanceRecord, CheckInSession
from schemas import AttendanceRecordOut, LeaderboardEntry
from auth import get_current_user, require_admin
from services.attendance import get_user_attendance, get_leaderboard

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


@router.get("/my", response_model=list[AttendanceRecordOut])
def my_attendance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = date.today()
    start = today.replace(day=1)
    return get_user_attendance(db, current_user.id, start, today)


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
def leaderboard(
    period: str = Query(..., pattern="^(week|month)$"),
    db: Session = Depends(get_db),
):
    results = get_leaderboard(db, period)
    return [
        LeaderboardEntry(rank=i + 1, **entry)
        for i, entry in enumerate(results)
    ]

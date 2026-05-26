from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import User, CheckInSession, AttendanceRecord
from config import VALID_ATTENDANCE_MINUTES, WEEKEND_TOTAL_MINUTES


def calculate_daily_attendance(db: Session, target_date: date) -> None:
    is_weekend = target_date.weekday() >= 5  # 5=Sat, 6=Sun

    users = db.query(User).all()
    for user in users:
        day_start = datetime.combine(target_date, datetime.min.time())
        day_end = day_start + timedelta(days=1)

        sessions = db.query(CheckInSession).filter(
            CheckInSession.user_id == user.id,
            CheckInSession.check_in_time >= day_start,
            CheckInSession.check_in_time < day_end,
            CheckInSession.check_out_time.isnot(None),
            CheckInSession.is_auto_checkout == False,
        ).all()

        total_minutes = sum(
            int((s.check_out_time - s.check_in_time).total_seconds() / 60)
            for s in sessions
        )

        existing = db.query(AttendanceRecord).filter(
            AttendanceRecord.user_id == user.id,
            AttendanceRecord.date == target_date,
        ).first()

        if existing:
            existing.total_minutes = total_minutes
            existing.is_weekend = is_weekend
            existing.is_valid = total_minutes >= VALID_ATTENDANCE_MINUTES
        else:
            record = AttendanceRecord(
                user_id=user.id,
                date=target_date,
                total_minutes=total_minutes,
                is_valid=total_minutes >= VALID_ATTENDANCE_MINUTES,
                is_weekend=is_weekend,
            )
            db.add(record)

    db.commit()


def apply_weekend_rule(db: Session, saturday: date, sunday: date) -> None:
    sat_records = db.query(AttendanceRecord).filter(
        AttendanceRecord.date == saturday,
        AttendanceRecord.is_weekend == True,
    ).all()

    for record in sat_records:
        sun_record = db.query(AttendanceRecord).filter(
            AttendanceRecord.user_id == record.user_id,
            AttendanceRecord.date == sunday,
            AttendanceRecord.is_weekend == True,
        ).first()

        if sun_record:
            sat_valid = record.total_minutes >= VALID_ATTENDANCE_MINUTES
            sun_valid = sun_record.total_minutes >= VALID_ATTENDANCE_MINUTES
            total = record.total_minutes + sun_record.total_minutes

            if sat_valid and sun_valid:
                record.is_valid = True
                sun_record.is_valid = True

    db.commit()


def get_user_attendance(db: Session, user_id: int, start_date: date, end_date: date) -> list[AttendanceRecord]:
    return db.query(AttendanceRecord).filter(
        AttendanceRecord.user_id == user_id,
        AttendanceRecord.date >= start_date,
        AttendanceRecord.date <= end_date,
    ).order_by(AttendanceRecord.date).all()


def get_leaderboard(db: Session, period: str) -> list[dict]:
    today = date.today()
    if period == "week":
        start_date = today - timedelta(days=today.weekday())
        days_count = (today - start_date).days + 1
        weekdays_count = sum(1 for i in range(days_count) if (start_date + timedelta(days=i)).weekday() < 5)
    else:
        start_date = today.replace(day=1)
        days_count = (today - start_date).days + 1
        weekdays_count = sum(1 for i in range(days_count) if (start_date + timedelta(days=i)).weekday() < 5)

    if weekdays_count == 0:
        weekdays_count = 1

    users = db.query(User).filter(User.role == "user").all()
    results = []

    for user in users:
        records = db.query(AttendanceRecord).filter(
            AttendanceRecord.user_id == user.id,
            AttendanceRecord.date >= start_date,
            AttendanceRecord.date <= today,
        ).all()

        valid_count = sum(1 for r in records if r.is_valid)
        total_minutes = sum(r.total_minutes for r in records)
        rate = valid_count / weekdays_count

        results.append({
            "user_id": user.id,
            "name": user.name,
            "attendance_rate": round(rate, 4),
            "valid_count": valid_count,
            "total_minutes": total_minutes,
        })

    results.sort(key=lambda x: (-x["attendance_rate"], -x["total_minutes"]))
    return results[:5]

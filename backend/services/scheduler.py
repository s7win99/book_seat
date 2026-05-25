from datetime import datetime, date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from database import SessionLocal
from models import CheckInSession
from services.attendance import calculate_daily_attendance, apply_weekend_rule


def auto_checkout_job():
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        active_sessions = db.query(CheckInSession).filter(
            CheckInSession.check_out_time.is_(None),
        ).all()

        for session in active_sessions:
            session.check_out_time = now
            session.is_auto_checkout = True

        db.commit()
        print(f"Auto checkout: {len(active_sessions)} sessions")
    finally:
        db.close()


def calculate_attendance_job():
    db = SessionLocal()
    try:
        yesterday = date.today() - timedelta(days=1)
        calculate_daily_attendance(db, yesterday)

        if yesterday.weekday() == 6:  # Sunday
            saturday = yesterday - timedelta(days=1)
            apply_weekend_rule(db, saturday, yesterday)

        print(f"Attendance calculated for {yesterday}")
    finally:
        db.close()


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(auto_checkout_job, "cron", hour=0, minute=0)
    scheduler.add_job(calculate_attendance_job, "cron", hour=0, minute=5)
    scheduler.start()
    return scheduler

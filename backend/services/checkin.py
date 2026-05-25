from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import User, Seat, CheckInSession, Cooldown
from config import COOLDOWN_MINUTES


class CheckInError(Exception):
    pass


def get_active_session(db: Session, user_id: int) -> CheckInSession | None:
    return db.query(CheckInSession).filter(
        CheckInSession.user_id == user_id,
        CheckInSession.check_out_time.is_(None),
    ).first()


def get_seat_occupant(db: Session, seat_id: int) -> User | None:
    session = db.query(CheckInSession).filter(
        CheckInSession.seat_id == seat_id,
        CheckInSession.check_out_time.is_(None),
    ).first()
    if session:
        return db.query(User).filter(User.id == session.user_id).first()
    return None


def check_cooldown(db: Session, user_id: int) -> bool:
    cooldown = db.query(Cooldown).filter(Cooldown.user_id == user_id).first()
    if not cooldown or not cooldown.last_switch_time:
        return True
    elapsed = datetime.utcnow() - cooldown.last_switch_time
    return elapsed >= timedelta(minutes=COOLDOWN_MINUTES)


def get_remaining_cooldown(db: Session, user_id: int) -> int:
    cooldown = db.query(Cooldown).filter(Cooldown.user_id == user_id).first()
    if not cooldown or not cooldown.last_switch_time:
        return 0
    elapsed = datetime.utcnow() - cooldown.last_switch_time
    remaining = timedelta(minutes=COOLDOWN_MINUTES) - elapsed
    return max(0, int(remaining.total_seconds()))


def perform_check_in(db: Session, user: User, seat: Seat, ip_address: str | None) -> CheckInSession:
    active = get_active_session(db, user.id)
    if active:
        raise CheckInError("already_checked_in")

    # Fixed seat: only assigned user can check in
    if seat.seat_type == "fixed":
        if seat.assigned_user_id != user.id:
            raise CheckInError("not_assigned_fixed_seat")
    else:
        # Shared seat: user with fixed seat cannot use shared seats
        has_fixed = db.query(Seat).filter(
            Seat.seat_type == "fixed",
            Seat.assigned_user_id == user.id,
        ).first()
        if has_fixed:
            raise CheckInError("user_has_fixed_seat")

    occupant = get_seat_occupant(db, seat.id)
    if occupant:
        raise CheckInError("seat_occupied")

    if not check_cooldown(db, user.id):
        raise CheckInError("cooldown_active")

    session = CheckInSession(
        user_id=user.id,
        seat_id=seat.id,
        check_in_time=datetime.utcnow(),
        ip_address=ip_address,
    )
    db.add(session)

    cooldown = db.query(Cooldown).filter(Cooldown.user_id == user.id).first()
    if cooldown:
        cooldown.last_switch_time = datetime.utcnow()
    else:
        db.add(Cooldown(user_id=user.id, last_switch_time=datetime.utcnow()))

    db.commit()
    db.refresh(session)
    return session


def perform_check_out(db: Session, user: User, seat_id: int) -> CheckInSession:
    active = get_active_session(db, user.id)
    if not active:
        raise CheckInError("not_checked_in")
    if active.seat_id != seat_id:
        raise CheckInError("wrong_seat")

    if not check_cooldown(db, user.id):
        raise CheckInError("cooldown_active")

    active.check_out_time = datetime.utcnow()
    db.commit()
    db.refresh(active)
    return active


def perform_switch_seat(db: Session, user: User, new_seat: Seat, ip_address: str | None) -> CheckInSession:
    active = get_active_session(db, user.id)
    if not active:
        raise CheckInError("not_checked_in")

    if not check_cooldown(db, user.id):
        raise CheckInError("cooldown_active")

    if new_seat.seat_type == "fixed":
        if new_seat.assigned_user_id != user.id:
            raise CheckInError("not_assigned_fixed_seat")
    else:
        has_fixed = db.query(Seat).filter(
            Seat.seat_type == "fixed",
            Seat.assigned_user_id == user.id,
        ).first()
        if has_fixed:
            raise CheckInError("user_has_fixed_seat")

    occupant = get_seat_occupant(db, new_seat.id)
    if occupant:
        raise CheckInError("seat_occupied")

    # Check out from old seat
    active.check_out_time = datetime.utcnow()
    db.flush()

    # Check in to new seat
    new_session = CheckInSession(
        user_id=user.id,
        seat_id=new_seat.id,
        check_in_time=datetime.utcnow(),
        ip_address=ip_address,
    )
    db.add(new_session)

    cooldown = db.query(Cooldown).filter(Cooldown.user_id == user.id).first()
    if cooldown:
        cooldown.last_switch_time = datetime.utcnow()
    else:
        db.add(Cooldown(user_id=user.id, last_switch_time=datetime.utcnow()))

    db.commit()
    db.refresh(new_session)
    return new_session

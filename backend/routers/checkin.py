from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import get_db
from models import User, Seat, CheckInSession
from schemas import CheckInRequest, CheckOutRequest, CheckInStatus
from auth import get_current_user
from services.checkin import (
    get_active_session,
    get_seat_occupant,
    get_remaining_cooldown,
    perform_check_in,
    perform_check_out,
    perform_switch_seat,
    CheckInError,
)
from datetime import datetime

router = APIRouter(prefix="/api", tags=["checkin"])


@router.post("/checkin")
def check_in(
    request: CheckInRequest,
    req: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    seat = db.query(Seat).filter(Seat.token == request.seat_token).first()
    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found")

    ip_address = req.client.host
    active = get_active_session(db, current_user.id)

    try:
        if active and active.seat_id == seat.id:
            raise CheckInError("already_at_this_seat")
        elif active:
            session = perform_switch_seat(db, current_user, seat, ip_address)
            return {"message": "Switched seat", "seat_name": seat.name}
        else:
            session = perform_check_in(db, current_user, seat, ip_address)
            return {"message": "Checked in", "seat_name": seat.name}
    except CheckInError as e:
        error_map = {
            "already_checked_in": (400, "You are already checked in"),
            "not_assigned_fixed_seat": (403, f"This seat is reserved for another user"),
            "user_has_fixed_seat": (403, f"You have a fixed seat, please check in there"),
            "seat_occupied": (409, "Seat is occupied"),
            "cooldown_active": (429, f"Cooldown active, please wait {get_remaining_cooldown(db, current_user.id)} seconds"),
            "already_at_this_seat": (400, "You are already at this seat"),
        }
        code, msg = error_map.get(str(e), (400, str(e)))
        raise HTTPException(status_code=code, detail=msg)


@router.post("/checkout")
def check_out(
    request: CheckOutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        session = perform_check_out(db, current_user, request.seat_id)
        duration = int((session.check_out_time - session.check_in_time).total_seconds() / 60)
        return {"message": "Checked out", "duration_minutes": duration}
    except CheckInError as e:
        error_map = {
            "not_checked_in": (400, "You are not checked in"),
            "wrong_seat": (400, "You are not checked into this seat"),
            "cooldown_active": (429, f"Cooldown active, please wait {get_remaining_cooldown(db, current_user.id)} seconds"),
        }
        code, msg = error_map.get(str(e), (400, str(e)))
        raise HTTPException(status_code=code, detail=msg)


@router.get("/checkin/status", response_model=CheckInStatus)
def checkin_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    active = get_active_session(db, current_user.id)
    if not active:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_sessions = db.query(CheckInSession).filter(
            CheckInSession.user_id == current_user.id,
            CheckInSession.check_in_time >= today_start,
            CheckInSession.is_auto_checkout == False,
        ).all()
        total = sum(
            int((s.check_out_time - s.check_in_time).total_seconds() / 60)
            for s in today_sessions if s.check_out_time
        )
        return CheckInStatus(is_checked_in=False, today_total_minutes=total)

    seat = db.query(Seat).filter(Seat.id == active.seat_id).first()
    elapsed = int((datetime.utcnow() - active.check_in_time).total_seconds() / 60)

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_sessions = db.query(CheckInSession).filter(
        CheckInSession.user_id == current_user.id,
        CheckInSession.check_in_time >= today_start,
        CheckInSession.is_auto_checkout == False,
        CheckInSession.id != active.id,
    ).all()
    total = sum(
        int((s.check_out_time - s.check_in_time).total_seconds() / 60)
        for s in today_sessions if s.check_out_time
    )

    return CheckInStatus(
        is_checked_in=True,
        seat_id=active.seat_id,
        seat_name=seat.name,
        check_in_time=active.check_in_time,
        elapsed_minutes=elapsed,
        today_total_minutes=total + elapsed,
    )

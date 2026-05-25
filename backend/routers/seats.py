from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import User, Seat, CheckInSession
from schemas import SeatOut
from auth import get_current_user
from services.checkin import get_seat_occupant

router = APIRouter(prefix="/api/seats", tags=["seats"])


@router.get("", response_model=list[SeatOut])
def list_seats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    seats = db.query(Seat).all()
    result = []
    for seat in seats:
        assigned_user = db.query(User).filter(User.id == seat.assigned_user_id).first() if seat.assigned_user_id else None
        occupant = get_seat_occupant(db, seat.id)
        result.append(SeatOut(
            id=seat.id,
            name=seat.name,
            seat_type=seat.seat_type,
            token=seat.token,
            assigned_user_id=seat.assigned_user_id,
            assigned_user_name=assigned_user.name if assigned_user else None,
            is_occupied=occupant is not None,
            occupant_name=occupant.name if occupant else None,
            occupant_user_id=occupant.id if occupant else None,
        ))
    return result


@router.get("/by-token/{token}")
def get_seat_by_token(token: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from services.checkin import get_active_session, check_cooldown, get_remaining_cooldown
    seat = db.query(Seat).filter(Seat.token == token).first()
    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found")

    assigned_user = db.query(User).filter(User.id == seat.assigned_user_id).first() if seat.assigned_user_id else None
    occupant = get_seat_occupant(db, seat.id)
    active = get_active_session(db, current_user.id)

    return {
        "id": seat.id,
        "name": seat.name,
        "seat_type": seat.seat_type,
        "assigned_user_id": seat.assigned_user_id,
        "assigned_user_name": assigned_user.name if assigned_user else None,
        "is_occupied": occupant is not None,
        "occupant_name": occupant.name if occupant else None,
        "current_user_checked_in": active is not None,
        "current_user_seat_id": active.seat_id if active else None,
        "cooldown_remaining": get_remaining_cooldown(db, current_user.id),
    }

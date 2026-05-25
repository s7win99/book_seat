from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import User, Seat, CheckInSession, AttendanceRecord
from schemas import UserCreate, UserUpdate, UserOut, SeatCreate, SeatUpdate, SeatOut
from auth import hash_password, require_admin
from datetime import datetime

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
def list_users(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(User).all()


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(request: UserCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == request.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    user = User(
        username=request.username,
        name=request.name,
        password_hash=hash_password(request.password),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, request: UserUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if request.name is not None:
        user.name = request.name
    if request.role is not None:
        user.role = request.role
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}")
def delete_user(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}


@router.post("/users/{user_id}/reset-password")
def reset_password(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password_hash = hash_password("123456")
    db.commit()
    return {"message": "Password reset to 123456"}


@router.get("/seats", response_model=list[SeatOut])
def list_seats_admin(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    seats = db.query(Seat).all()
    result = []
    for seat in seats:
        assigned_user = db.query(User).filter(User.id == seat.assigned_user_id).first() if seat.assigned_user_id else None
        active_session = db.query(CheckInSession).filter(
            CheckInSession.seat_id == seat.id,
            CheckInSession.check_out_time.is_(None),
        ).first()
        occupant = db.query(User).filter(User.id == active_session.user_id).first() if active_session else None
        result.append(SeatOut(
            id=seat.id,
            name=seat.name,
            seat_type=seat.seat_type,
            token=seat.token,
            assigned_user_id=seat.assigned_user_id,
            assigned_user_name=assigned_user.name if assigned_user else None,
            is_occupied=active_session is not None,
            occupant_name=occupant.name if occupant else None,
            occupant_user_id=occupant.id if occupant else None,
        ))
    return result


@router.post("/seats", response_model=SeatOut, status_code=201)
def create_seat(request: SeatCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    import secrets
    token = secrets.token_urlsafe(32)
    seat = Seat(
        name=request.name,
        seat_type=request.seat_type,
        token=token,
        assigned_user_id=request.assigned_user_id,
    )
    db.add(seat)
    db.commit()
    db.refresh(seat)
    assigned_user = db.query(User).filter(User.id == seat.assigned_user_id).first() if seat.assigned_user_id else None
    return SeatOut(
        id=seat.id,
        name=seat.name,
        seat_type=seat.seat_type,
        token=seat.token,
        assigned_user_id=seat.assigned_user_id,
        assigned_user_name=assigned_user.name if assigned_user else None,
    )


@router.put("/seats/{seat_id}", response_model=SeatOut)
def update_seat(seat_id: int, request: SeatUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    seat = db.query(Seat).filter(Seat.id == seat_id).first()
    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found")
    if request.name is not None:
        seat.name = request.name
    if request.seat_type is not None:
        seat.seat_type = request.seat_type
    if request.assigned_user_id is not None:
        seat.assigned_user_id = request.assigned_user_id
    db.commit()
    db.refresh(seat)
    assigned_user = db.query(User).filter(User.id == seat.assigned_user_id).first() if seat.assigned_user_id else None
    return SeatOut(
        id=seat.id,
        name=seat.name,
        seat_type=seat.seat_type,
        token=seat.token,
        assigned_user_id=seat.assigned_user_id,
        assigned_user_name=assigned_user.name if assigned_user else None,
    )


@router.delete("/seats/{seat_id}")
def delete_seat(seat_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    seat = db.query(Seat).filter(Seat.id == seat_id).first()
    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found")
    active = db.query(CheckInSession).filter(
        CheckInSession.seat_id == seat_id,
        CheckInSession.check_out_time.is_(None),
    ).first()
    if active:
        raise HTTPException(status_code=400, detail="Seat is currently occupied")
    db.delete(seat)
    db.commit()
    return {"message": "Seat deleted"}


@router.post("/seats/{seat_id}/refresh-token", response_model=SeatOut)
def refresh_seat_token(seat_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    import secrets
    seat = db.query(Seat).filter(Seat.id == seat_id).first()
    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found")
    seat.token = secrets.token_urlsafe(32)
    db.commit()
    db.refresh(seat)
    assigned_user = db.query(User).filter(User.id == seat.assigned_user_id).first() if seat.assigned_user_id else None
    return SeatOut(
        id=seat.id,
        name=seat.name,
        seat_type=seat.seat_type,
        token=seat.token,
        assigned_user_id=seat.assigned_user_id,
        assigned_user_name=assigned_user.name if assigned_user else None,
    )


@router.post("/force-checkout/{user_id}")
def force_checkout(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    active = db.query(CheckInSession).filter(
        CheckInSession.user_id == user_id,
        CheckInSession.check_out_time.is_(None),
    ).first()
    if not active:
        raise HTTPException(status_code=400, detail="User is not checked in")
    active.check_out_time = datetime.utcnow()
    db.commit()
    return {"message": f"Force checked out {user.name}"}

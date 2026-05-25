from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database import get_db
from models import User, Seat, CheckInSession, AttendanceRecord
from schemas import UserCreate, UserUpdate, UserOut, SeatCreate, SeatUpdate, SeatOut, AttendanceRecordOut
from auth import hash_password, require_admin, require_superadmin
from datetime import datetime, date
import io
import qrcode

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


@router.put("/users/{user_id}/role")
def change_user_role(
    user_id: int,
    role: str = Query(...),
    admin: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    if role not in ("user", "admin", "superadmin"):
        raise HTTPException(status_code=400, detail="Invalid role")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")
    user.role = role
    db.commit()
    return {"message": f"Role changed to {role}"}


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


@router.get("/attendance")
def admin_attendance(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not start_date:
        start_date = date.today().replace(day=1)
    if not end_date:
        end_date = date.today()

    users = db.query(User).filter(User.role == "user").all()
    result = []
    for user in users:
        records = db.query(AttendanceRecord).filter(
            AttendanceRecord.user_id == user.id,
            AttendanceRecord.date >= start_date,
            AttendanceRecord.date <= end_date,
        ).order_by(AttendanceRecord.date).all()

        result.append({
            "user_id": user.id,
            "username": user.username,
            "name": user.name,
            "records": records,
            "total_valid": sum(1 for r in records if r.is_valid),
            "total_minutes": sum(r.total_minutes for r in records),
        })
    return result


@router.get("/seats/{seat_id}/qrcode")
def get_seat_qrcode(seat_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    seat = db.query(Seat).filter(Seat.id == seat_id).first()
    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found")

    url = f"http://localhost:5173/checkin?token={seat.token}"
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")

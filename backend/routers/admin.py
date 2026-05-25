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


@router.post("/seats/refresh-all-tokens", response_model=list[SeatOut])
def refresh_all_tokens(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    import secrets
    seats = db.query(Seat).all()
    for seat in seats:
        seat.token = secrets.token_urlsafe(32)
    db.commit()
    # Return updated list
    result = []
    for seat in seats:
        db.refresh(seat)
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


@router.post("/cancel-checkin/{user_id}")
def cancel_checkin(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    from models import Cooldown
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    active = db.query(CheckInSession).filter(
        CheckInSession.user_id == user_id,
        CheckInSession.check_out_time.is_(None),
    ).first()
    if not active:
        raise HTTPException(status_code=404, detail="该用户当前没有签到")
    # Delete the session so time is not recorded
    db.delete(active)
    # Clear cooldown so user can check in again immediately
    cooldown = db.query(Cooldown).filter(Cooldown.user_id == user_id).first()
    if cooldown:
        db.delete(cooldown)
    db.commit()
    return {"message": f"已取消 {user.name} 的签到"}


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
    from PIL import Image, ImageDraw, ImageFont

    seat = db.query(Seat).filter(Seat.id == seat_id).first()
    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found")

    url = f"http://localhost:5173/checkin?token={seat.token}"
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    # Create canvas: QR code + space for text below
    qr_w, qr_h = qr_img.size
    text_height = 40
    canvas = Image.new("RGB", (qr_w, qr_h + text_height), "white")
    canvas.paste(qr_img, (0, 0))

    # Draw seat name centered below QR code
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=20)
    bbox = draw.textbbox((0, 0), seat.name, font=font)
    text_w = bbox[2] - bbox[0]
    text_x = (qr_w - text_w) // 2
    text_y = qr_h + 8
    draw.text((text_x, text_y), seat.name, fill="black", font=font)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@router.get("/seats/qrcode-batch")
def batch_qrcode(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    import zipfile
    from PIL import Image, ImageDraw, ImageFont

    seats = db.query(Seat).all()
    if not seats:
        raise HTTPException(status_code=400, detail="没有座位可导出")

    def generate_labeled_qr(seat):
        url = f"http://localhost:5173/checkin?token={seat.token}"
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        qr_w, qr_h = qr_img.size
        text_height = 40
        canvas = Image.new("RGB", (qr_w, qr_h + text_height), "white")
        canvas.paste(qr_img, (0, 0))
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.load_default(size=20)
        bbox = draw.textbbox((0, 0), seat.name, font=font)
        text_w = bbox[2] - bbox[0]
        text_x = (qr_w - text_w) // 2
        draw.text((text_x, qr_h + 8), seat.name, fill="black", font=font)
        return canvas

    # A4 at 300 DPI
    page_w, page_h = 2480, 3508
    cols, rows = 3, 3
    per_page = cols * rows
    margin_x, margin_y = 100, 100
    gap_x, gap_y = 50, 70
    cell_w = (page_w - 2 * margin_x - (cols - 1) * gap_x) // cols
    cell_h = (page_h - 2 * margin_y - (rows - 1) * gap_y) // rows

    # Scale QR to fit in cell (leave room for text)
    qr_target_h = cell_h - 80
    qr_target_w = cell_w - 40

    pages = []
    for page_start in range(0, len(seats), per_page):
        page_seats = seats[page_start:page_start + per_page]
        page = Image.new("RGB", (page_w, page_h), "white")
        for idx, seat in enumerate(page_seats):
            row = idx // cols
            col = idx % cols
            labeled_qr = generate_labeled_qr(seat)
            # Resize to fit cell
            scale = min(qr_target_w / labeled_qr.size[0], qr_target_h / labeled_qr.size[1])
            new_size = (int(labeled_qr.size[0] * scale), int(labeled_qr.size[1] * scale))
            labeled_qr = labeled_qr.resize(new_size, Image.LANCZOS)
            # Center in cell
            x = margin_x + col * (cell_w + gap_x) + (cell_w - new_size[0]) // 2
            y = margin_y + row * (cell_h + gap_y) + (cell_h - new_size[1]) // 2
            page.paste(labeled_qr, (x, y))
        pages.append(page)

    if len(pages) == 1:
        buf = io.BytesIO()
        pages[0].save(buf, format="PNG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")

    # Multiple pages: return ZIP
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, page in enumerate(pages):
            page_buf = io.BytesIO()
            page.save(page_buf, format="PNG")
            page_buf.seek(0)
            zf.writestr(f"qrcode_page{i + 1}.png", page_buf.read())
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip", headers={"Content-Disposition": "attachment; filename=qrcodes.zip"})

from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UserCreate(BaseModel):
    username: str
    name: str
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None


class UserOut(BaseModel):
    id: int
    username: str
    name: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class SeatCreate(BaseModel):
    name: str
    seat_type: str  # "fixed" or "shared"
    assigned_user_id: Optional[int] = None


class SeatUpdate(BaseModel):
    name: Optional[str] = None
    seat_type: Optional[str] = None
    assigned_user_id: Optional[int] = None


class SeatOut(BaseModel):
    id: int
    name: str
    seat_type: str
    token: str
    assigned_user_id: Optional[int]
    assigned_user_name: Optional[str] = None
    is_occupied: bool = False
    occupant_name: Optional[str] = None
    occupant_user_id: Optional[int] = None

    class Config:
        from_attributes = True


class SeatDetailByToken(BaseModel):
    id: int
    name: str
    seat_type: str
    assigned_user_id: Optional[int]
    assigned_user_name: Optional[str] = None
    is_occupied: bool = False
    occupant_name: Optional[str] = None
    current_user_checked_in: bool = False
    current_user_seat_id: Optional[int] = None


class CheckInRequest(BaseModel):
    seat_token: str


class CheckOutRequest(BaseModel):
    seat_id: int


class CheckInStatus(BaseModel):
    is_checked_in: bool
    seat_id: Optional[int] = None
    seat_name: Optional[str] = None
    check_in_time: Optional[datetime] = None
    elapsed_minutes: Optional[int] = None
    today_total_minutes: int = 0


class CheckInSessionOut(BaseModel):
    id: int
    seat_name: str
    check_in_time: datetime
    check_out_time: Optional[datetime]
    is_auto_checkout: bool
    duration_minutes: Optional[int]

    class Config:
        from_attributes = True


class AttendanceRecordOut(BaseModel):
    id: int
    date: date
    total_minutes: int
    is_valid: bool
    is_weekend: bool

    class Config:
        from_attributes = True


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    name: str
    attendance_rate: float
    valid_count: int
    total_minutes: int


class AdminAttendanceOut(BaseModel):
    user_id: int
    username: str
    name: str
    records: list[AttendanceRecordOut]
    total_valid: int
    total_minutes: int

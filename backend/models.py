from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)  # "user" or "admin"
    created_at = Column(DateTime, default=datetime.utcnow)

    seats = relationship("Seat", back_populates="assigned_user")
    checkin_sessions = relationship("CheckInSession", back_populates="user")
    attendance_records = relationship("AttendanceRecord", back_populates="user")


class Seat(Base):
    __tablename__ = "seats"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    seat_type = Column(String, nullable=False)  # "fixed" or "shared"
    token = Column(String, unique=True, index=True, nullable=False)
    assigned_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    assigned_user = relationship("User", back_populates="seats")
    checkin_sessions = relationship("CheckInSession", back_populates="seat")


class CheckInSession(Base):
    __tablename__ = "checkin_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    seat_id = Column(Integer, ForeignKey("seats.id"), nullable=False)
    check_in_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    check_out_time = Column(DateTime, nullable=True)
    is_auto_checkout = Column(Boolean, default=False)
    ip_address = Column(String, nullable=True)

    user = relationship("User", back_populates="checkin_sessions")
    seat = relationship("Seat", back_populates="checkin_sessions")


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    total_minutes = Column(Integer, default=0)
    is_valid = Column(Boolean, default=False)
    is_weekend = Column(Boolean, default=False)

    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_user_date"),)

    user = relationship("User", back_populates="attendance_records")


class Cooldown(Base):
    __tablename__ = "cooldowns"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    last_switch_time = Column(DateTime, nullable=True)

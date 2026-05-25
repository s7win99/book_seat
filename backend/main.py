from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
import models  # noqa: F401
from routers import auth, admin, checkin, seats, attendance
from services.scheduler import start_scheduler

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Lab Attendance System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(checkin.router)
app.include_router(seats.router)
app.include_router(attendance.router)

scheduler = start_scheduler()


@app.get("/api/health")
def health_check():
    return {"status": "ok"}

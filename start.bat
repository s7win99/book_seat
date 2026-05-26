@echo off
echo Starting Lab Attendance System...
echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo.

start "Backend" cmd /c "cd backend && python -m uvicorn main:app --reload --port 8000"
start "Frontend" cmd /c "cd frontend && npm run dev"

echo Both services are starting in separate windows.
echo Close this window or press any key to exit.
pause > nul

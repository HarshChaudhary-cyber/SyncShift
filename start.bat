@echo off
TITLE SyncShift Launcher
echo ============================================================
echo   SyncShift - Student/Work Schedule Conflict Assistant
echo ============================================================
echo.

SET "ROOT_DIR=%~dp0"

echo [1/2] Launching Backend Server (FastAPI on http://127.0.0.1:8000)...
start "SyncShift Backend" cmd /k "cd /d "%ROOT_DIR%backend" && if exist .venv\Scripts\activate.bat (call .venv\Scripts\activate.bat) && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

echo [2/2] Launching Frontend Server (Next.js on http://localhost:3000)...
start "SyncShift Frontend" cmd /k "cd /d "%ROOT_DIR%app" && npm.cmd run dev"

echo.
echo ============================================================
echo   Both services are launching in separate windows:
echo   - Frontend: http://localhost:3000
echo   - Backend:  http://127.0.0.1:8000
echo   - Swagger:  http://127.0.0.1:8000/docs
echo ============================================================
echo.
pause

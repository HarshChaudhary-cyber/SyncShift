@echo off
REM ============================================================
REM  SyncShift Backend – Startup Script (Windows)
REM ============================================================

SET "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo.
echo [SyncShift] Checking virtual environment...
IF NOT EXIST ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found at .venv\
    echo         Run: python -m venv .venv
    echo         Then: .venv\Scripts\pip install -r requirements.txt
    exit /b 1
)

echo [SyncShift] Activating virtual environment...
call .venv\Scripts\activate.bat

echo [SyncShift] Checking dependencies...
python -c "import fastapi, uvicorn" 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo [WARN] Dependencies missing. Installing from requirements.txt...
    pip install -r requirements.txt
)

echo.
echo [SyncShift] Starting FastAPI server on http://localhost:8000
echo [SyncShift] Press Ctrl+C to stop.
echo.

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Server failed to start. Check the output above.
    pause
)

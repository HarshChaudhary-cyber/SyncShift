#!/usr/bin/env bash
# SyncShift - Student/Work Schedule Conflict Assistant
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "============================================================"
echo "  Starting SyncShift Backend & Frontend"
echo "============================================================"

# Start backend
echo "[1/2] Starting Backend on http://127.0.0.1:8000..."
cd "$DIR/backend"
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Start frontend
echo "[2/2] Starting Frontend on http://localhost:3000..."
cd "$DIR/app"
npm run dev &
FRONTEND_PID=$!

trap "echo 'Stopping SyncShift...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT INT TERM

echo ""
echo "SyncShift running!"
echo "- Frontend: http://localhost:3000"
echo "- Backend:  http://127.0.0.1:8000"
echo "- API Docs: http://127.0.0.1:8000/docs"
echo "Press Ctrl+C to stop both servers."
wait

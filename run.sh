#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "=========================================================="
echo "          GoWiki Autonomous Documentation & Chat          "
echo "=========================================================="

# Check Python environment
if [ -f "$ROOT_DIR/backend/venv/bin/python3" ]; then
    PYTHON_BIN="$ROOT_DIR/backend/venv/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
else
    echo "[-] Error: python3 not found."
    exit 1
fi

echo "[+] Using Python runtime: $PYTHON_BIN"

# Check Node environment
if ! command -v npm >/dev/null 2>&1; then
    echo "[-] Error: npm not found."
    exit 1
fi

echo "[+] Using Node: $(node -v) / npm: $(npm -v)"

# Trap for graceful shutdown of child processes
cleanup() {
    echo ""
    echo "[!] Stopping GoWiki services..."
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    wait 2>/dev/null || true
    echo "[+] All services stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# Start FastAPI Backend on port 8000
echo "[*] Launching Backend Service (FastAPI) on port 8000..."
PYTHONPATH="$ROOT_DIR" "$PYTHON_BIN" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend health
echo "[*] Waiting for backend readiness..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:8000/health >/dev/null 2>&1; then
        echo "[+] Backend healthy at http://localhost:8000"
        break
    fi
    sleep 0.5
done

# Start Next.js Frontend on port 3000
echo "[*] Launching Frontend Web Application (Next.js) on port 3000..."
npx next dev --port 3000 &
FRONTEND_PID=$!

echo ""
echo "=========================================================="
echo " GoWiki Running!"
echo "   - Web Surface:    http://localhost:3000"
echo "   - Ingest Pipeline http://localhost:3000/generate"
echo "   - Wiki Reader:    http://localhost:3000/wiki"
echo "   - Reasoning Chat: http://localhost:3000/chat"
echo "   - Backend API:    http://localhost:8000/docs"
echo "=========================================================="
echo "Press Ctrl+C to stop all services."
echo ""

wait $FRONTEND_PID $BACKEND_PID

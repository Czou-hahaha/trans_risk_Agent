#!/usr/bin/env bash
# Start V2 backend (8001) + frontend (8000). Requires Postgres on :5433.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="${ROOT}/.venv/bin/python3"
if [[ ! -x "$PY" ]]; then
  echo "Creating venv with Python 3.10+ ..."
  /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m venv .venv
  .venv/bin/pip install -q -U pip
  .venv/bin/pip install -q -r engine/requirements.txt -r backend/requirements.txt
fi

export PYTHONPATH="${ROOT}/backend:${ROOT}/engine"
export BACKEND_PORT="${BACKEND_PORT:-8001}"

echo "Starting backend on http://localhost:${BACKEND_PORT} ..."
(cd "$ROOT/backend" && "$PY" -m uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT") &
BACKEND_PID=$!

sleep 2
if ! curl -sf "http://localhost:${BACKEND_PORT}/api/health" >/dev/null; then
  echo "Backend failed to start. Check Postgres (port 5433) and v2/.env"
  kill "$BACKEND_PID" 2>/dev/null || true
  exit 1
fi

echo "Starting frontend on http://localhost:8000 ..."
(cd "$ROOT/frontend" && npm run dev) &
FRONTEND_PID=$!

trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null' EXIT
echo ""
echo "Open: http://localhost:8000"
echo "API:  http://localhost:${BACKEND_PORT}/api/health"
wait

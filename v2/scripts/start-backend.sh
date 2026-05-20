#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
export PYTHONPATH="$ROOT/backend:$ROOT/engine"
exec uvicorn app.main:app --reload --host 0.0.0.0 --port "${BACKEND_PORT:-8001}"

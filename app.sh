#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
LOCAL_NODE_DIR="$ROOT_DIR/tools/node-v20.18.0-darwin-arm64/bin"
LOCAL_NPM_CLI="$ROOT_DIR/tools/node-v20.18.0-darwin-arm64/lib/node_modules/npm/bin/npm-cli.js"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/pip" install -r "$ROOT_DIR/backend/requirements.txt"

if [[ -x "$LOCAL_NODE_DIR/node" && -f "$LOCAL_NPM_CLI" ]]; then
  NPM_PATH="$LOCAL_NODE_DIR:$PATH"
  NODE_CMD=("$LOCAL_NODE_DIR/node")
  NPM_CMD=("$LOCAL_NODE_DIR/node" "$LOCAL_NPM_CLI")
elif command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
  NPM_PATH="$PATH"
  NODE_CMD=("$(command -v node)")
  NPM_CMD=("$(command -v npm)")
else
  echo "Node.js is required. Install Node or place the local runtime under tools/."
  exit 1
fi

if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
  (
    cd "$ROOT_DIR/frontend"
    PATH="$NPM_PATH" "${NPM_CMD[@]}" install
  )
fi

require_free_port() {
  local port="$1"
  local label="$2"

  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "$label port $port is already in use. Stop the existing process and rerun ./app.sh."
    lsof -nP -iTCP:"$port" -sTCP:LISTEN
    exit 1
  fi
}

wait_for_backend() {
  local attempts=0

  while (( attempts < 50 )); do
    if ! kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
      echo "Backend exited before it became ready."
      wait "$BACKEND_PID"
    fi
    if curl -fsS http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
      return 0
    fi
    attempts=$((attempts + 1))
    sleep 0.2
  done

  echo "Backend did not become ready on http://127.0.0.1:8000."
  exit 1
}

require_free_port 8000 "Backend"
require_free_port 5173 "Frontend"

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${FRONTEND_PID:-}" ]]; then
    kill "$FRONTEND_PID" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT INT TERM

(
  cd "$ROOT_DIR"
  "$VENV_DIR/bin/python" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
) &
BACKEND_PID=$!

wait_for_backend

(
  cd "$ROOT_DIR/frontend"
  PATH="$NPM_PATH" "${NPM_CMD[@]}" run dev -- --host 127.0.0.1 --port 5173 --strictPort
) &
FRONTEND_PID=$!

wait "$BACKEND_PID" "$FRONTEND_PID"

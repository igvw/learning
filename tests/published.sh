#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PROJECT_NAME="learning-published"
DEPLOY_ARGS=(-p "$PROJECT_NAME" -f docker-compose.deploy.yml)

usage() {
  cat <<'EOF'
Usage:
  bash ./tests/published.sh up
  bash ./tests/published.sh down
EOF
}

case "${1:-}" in
  up)
    docker compose stop
    docker compose "${DEPLOY_ARGS[@]}" pull
    docker compose "${DEPLOY_ARGS[@]}" up -d
    ;;
  down)
    docker compose "${DEPLOY_ARGS[@]}" down -v
    ;;
  *)
    usage
    exit 1
    ;;
esac

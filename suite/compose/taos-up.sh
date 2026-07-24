#!/usr/bin/env bash
# Bring up / verify the taOS controller for the suite.
#
# taOS is not a docker-compose stack by default — the controller is a uvicorn
# service (install-server.sh registers it as tinyagentos.service on :6969).
# This script verifies it's reachable, and can start it from a source checkout
# if TAOS_SRC points at one. Workers are enrolled separately (install-worker).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SUITE_ENV:-$HERE/../suite.env}"
[ -f "$ENV_FILE" ] && { set -a; . "$ENV_FILE"; set +a; }
URL="${TAOS_CONTROLLER_URL:-http://localhost:6969}"

if curl -fsS "$URL/api/status" >/dev/null 2>&1; then
  echo "→ taOS controller already up at $URL"
  exit 0
fi

if [ -n "${TAOS_SRC:-}" ] && [ -d "$TAOS_SRC" ]; then
  echo "→ starting controller from $TAOS_SRC (uvicorn :6969)"
  ( cd "$TAOS_SRC" && exec python -m uvicorn tinyagentos.app:create_app \
      --factory --host 0.0.0.0 --port 6969 ) &
  for i in $(seq 1 30); do
    sleep 2
    curl -fsS "$URL/api/status" >/dev/null 2>&1 && { echo "  up"; exit 0; }
  done
  echo "  controller did not become ready in time" >&2; exit 1
fi

echo "taOS controller not reachable at $URL and TAOS_SRC not set." >&2
echo "Install it (scripts/install-server.sh) or run from source, then re-run." >&2
exit 1

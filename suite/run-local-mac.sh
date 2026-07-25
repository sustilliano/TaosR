#!/usr/bin/env bash
# One-shot local run for taOS on macOS (Apple Silicon).
#
# Builds the desktop UI, sets up the Python venv (+ litellm), and launches the
# controller — all from ONE repo root, derived from this script's location. So
# you can't accidentally build the UI in one checkout and run the server from
# another (the classic "/desktop 404 — desktop not installed" trap: the
# controller serves static/desktop/, which only exists in the checkout you
# actually built).
#
# Usage (from a checkout that has this file):
#   ./suite/run-local-mac.sh                 # build if needed, then run
#   ./suite/run-local-mac.sh --rebuild-ui    # force a fresh UI build
#   TAOS_PORT=6969 ./suite/run-local-mac.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
PORT="${TAOS_PORT:-6969}"
# The controller serves the SPA from here (routes/desktop.py: SPA_DIR =
# <repo>/static/desktop; vite build outDir = ../static/desktop).
SPA_INDEX="$REPO_ROOT/static/desktop/index.html"

log() { printf '\033[1;36m[suite]\033[0m %s\n' "$*"; }

# --- 1. desktop UI -> static/desktop/ ---
if [ ! -f "$SPA_INDEX" ] || [ "${1:-}" = "--rebuild-ui" ]; then
  log "building desktop UI (npm install && npm run build -> static/desktop/) …"
  ( cd "$REPO_ROOT/desktop" && npm install && npm run build )
  [ -f "$SPA_INDEX" ] || { log "UI build did not produce $SPA_INDEX — check the npm output above"; exit 1; }
else
  log "desktop UI present ($SPA_INDEX) — pass --rebuild-ui to rebuild"
fi

# --- 2. python venv + deps (this root's own .venv) ---
if [ ! -d "$REPO_ROOT/.venv" ]; then
  log "creating .venv …"
  python3 -m venv "$REPO_ROOT/.venv"
fi
# shellcheck disable=SC1091
source "$REPO_ROOT/.venv/bin/activate"
# Put cargo/rustc on PATH so Rust-built litellm deps compile (rustup users).
[ -f "$HOME/.cargo/env" ] && source "$HOME/.cargo/env"

if ! python -c "import tinyagentos" >/dev/null 2>&1; then
  log "installing taOS into the venv (pip install -e .) …"
  pip install -e "$REPO_ROOT"
fi
if ! python -c "import litellm" >/dev/null 2>&1; then
  log "installing litellm[proxy] (needs rustc/cargo on PATH) …"
  pip install 'litellm[proxy]>=1.92.0' 'prisma>=0.11.0' \
    || log "litellm install failed — controller still runs, just no model proxy. Fix cargo/PATH, rerun."
fi

# --- 3. launch ---
log "controller: http://localhost:$PORT"
log "FIRST RUN → create your login at http://localhost:$PORT/auth/setup"
log "(no container backend on mac = agents disabled until you install Docker; the UI works without it)"
exec python -m uvicorn tinyagentos.app:create_app --factory --host 0.0.0.0 --port "$PORT"

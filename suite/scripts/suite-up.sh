#!/usr/bin/env bash
# taos-suite orchestrator — bring taOS + open-cowork up as one environment.
#
# Non-destructive composition (docs/design/suite-combination-plan.md): this
# only verifies/starts the controller, writes cowork's MCP connectors, and
# registers cowork as a bean subject. It edits neither repo's source.
#
# Steps:
#   1. ensure the taOS controller is up (compose/taos-up.sh)
#   2. wire the taOS MCP connectors into open-cowork (plain-JSON store)
#   3. register app:open-cowork on the bean ledger (provenance + consent)
#   4. print the provider Settings to paste (encrypted store — manual)
set -euo pipefail

SUITE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export SUITE_ENV="${SUITE_ENV:-$SUITE_ROOT/suite.env}"
[ -f "$SUITE_ENV" ] || { echo "Copy suite.env.example -> suite.env and edit it first." >&2; exit 1; }
set -a; . "$SUITE_ENV"; set +a

echo "=== 1/4 taOS controller ==="
bash "$SUITE_ROOT/compose/taos-up.sh"

echo "=== 2/4 open-cowork MCP connectors ==="
bash "$SUITE_ROOT/clients/open-cowork/wire-cowork-mcp.sh" || \
  echo "  (skipped — launch open-cowork once so its config dir exists, then re-run)"

echo "=== 3/4 bean management (app:open-cowork) ==="
REG="${TAOS_BRIDGE_DIR:-$SUITE_ROOT/..}/integrations/open-cowork/register-cowork-bean.sh"
if [ -x "$REG" ] && [ -n "${TAOS_LOCAL_TOKEN:-}" ]; then
  TAOS_URL="$TAOS_CONTROLLER_URL" TAOS_LOCAL_TOKEN="$TAOS_LOCAL_TOKEN" \
    COWORK_MODEL="${COWORK_MODEL:-hermes-3-llama-3.1-8b}" \
    bash "$REG" ${COWORK_BEAN_SCOPES:-drive stop ptz_move} || echo "  (bean register failed — check TAOS_LOCAL_TOKEN)"
else
  echo "  (skipped — set TAOS_LOCAL_TOKEN in suite.env; register script at $REG)"
fi

echo "=== 4/4 model provider (manual — cowork's provider store is encrypted) ==="
cat <<EOF
  Open open-cowork → Settings → Provider (Custom / OpenAI-compatible):
    Base URL:  ${TAOS_LITELLM_URL:-http://localhost:4000/v1}
    API Key:   ${TAOS_LLM_KEY:-<a taOS LiteLLM key>}
    Model:     ${COWORK_MODEL:-hermes-3-llama-3.1-8b}
  Then restart open-cowork. It now runs on your taOS Hermes, drives taOS via
  MCP, and is governed as app:open-cowork on the bean ledger.
EOF
echo "Suite up."

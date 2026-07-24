#!/usr/bin/env bash
# Register open-cowork as a managed bean subject on a taOS controller.
#
# Puts the cowork desktop "under bean management" (docs/design/
# silicon-bean-all-digital.md + open-cowork-integration.md):
#   1. a Bean-0 provenance record for the cowork app, and
#   2. default-closed consent grants for the gated capabilities you allow,
#      keyed by the subject `app:open-cowork` on the shared consent ledger.
#
# Consent is default-closed: cowork can call a gated capability (drive, stop,
# ptz_move, app.net, …) only for scopes you grant here. Revoke any time with
# the /consent/revoke endpoint; it takes effect on the next call.
#
# Usage:
#   TAOS_URL=http://taos-controller:6969 \
#   TAOS_LOCAL_TOKEN=... \
#   COWORK_MODEL=hermes-3-llama-3.1-8b \
#   ./register-cowork-bean.sh drive stop ptz_move        # scopes to grant
set -euo pipefail

TAOS_URL="${TAOS_URL:?set TAOS_URL to your controller, e.g. http://taos-controller:6969}"
TOKEN="${TAOS_LOCAL_TOKEN:?set TAOS_LOCAL_TOKEN (controller local token)}"
MODEL="${COWORK_MODEL:-hermes-3-llama-3.1-8b}"
SUBJECT="app:open-cowork"
AUTH=(-H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json")

echo "→ provenance for open-cowork (model=${MODEL})"
curl -fsS -X POST "${TAOS_URL}/api/agents/open-cowork/provenance" "${AUTH[@]}" -d @- <<JSON >/dev/null
{
  "substrate": "silicon",
  "framework": "open-cowork",
  "framework_ref": "root-fork",
  "model_id": "${MODEL}",
  "corpus_refs": ["https://huggingface.co/datasets/teknium/OpenHermes-2.5"],
  "recorded_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON
echo "  ok"

for scope in "$@"; do
  echo "→ grant consent: ${SUBJECT} -> ${scope}"
  curl -fsS -X POST "${TAOS_URL}/api/agents/${SUBJECT}/consent/grant" "${AUTH[@]}" \
    -d "{\"scope\": \"${scope}\", \"granted_by\": \"$(whoami)@register-cowork-bean\"}" >/dev/null \
    && echo "  granted" \
    || echo "  FAILED (controller may predate the all-digital consent spine)"
done

echo "→ current grants for ${SUBJECT}:"
curl -fsS "${TAOS_URL}/api/agents/${SUBJECT}/consent" "${AUTH[@]}" || true
echo
echo "Done. cowork is now a managed bean subject; ungranted gated capabilities stay default-closed."

#!/usr/bin/env bash
# Merge the taOS bean-service MCP connectors into open-cowork's config.
#
# cowork's MCP store (electron-store name 'mcp-config') is PLAIN JSON
# {servers:[...]}, so it is safe to write from outside — unlike the provider
# config store, which is encrypted (do that one in Settings; see suite-up.sh).
#
# Idempotent: servers are matched by name; existing taOS entries are replaced,
# others left untouched. Reads paths/URLs from suite.env.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SUITE_ENV:-$HERE/../../suite.env}"
[ -f "$ENV_FILE" ] || { echo "no suite.env — copy suite.env.example first" >&2; exit 1; }
# shellcheck disable=SC1090
set -a; . "$ENV_FILE"; set +a

: "${TAOS_BRIDGE_DIR:?set TAOS_BRIDGE_DIR in suite.env}"

# Locate cowork's electron-store dir (projectName 'open-cowork').
find_cowork_dir() {
  for d in \
    "${COWORK_CONFIG_DIR:-}" \
    "$HOME/.config/open-cowork" \
    "$HOME/Library/Application Support/open-cowork" \
    "${APPDATA:-}/open-cowork"; do
    [ -n "$d" ] && [ -d "$d" ] && { echo "$d"; return 0; }
  done
  return 1
}

CFG_DIR="$(find_cowork_dir || true)"
if [ -z "$CFG_DIR" ]; then
  echo "Could not find open-cowork's config dir. Launch open-cowork once, or set COWORK_CONFIG_DIR." >&2
  exit 1
fi
MCP_JSON="$CFG_DIR/mcp-config.json"
echo "→ wiring taOS connectors into $MCP_JSON"

python3 - "$MCP_JSON" <<'PY'
import json, os, sys, uuid

mcp_path = sys.argv[1]
bridge = os.environ["TAOS_BRIDGE_DIR"].rstrip("/")
tank_url = os.environ.get("TAOS_TANK_COORDINATOR_URL", "http://localhost:8420")
tmrfs_url = os.environ.get("TAOS_TMRFS_URL", "http://localhost:8080")
pk_toolchain = os.environ.get("PK_VSE_TOOLCHAIN", "/opt/planekey-vse/toolchain")
pk_ws = os.environ.get("PK_WORKSPACE", "/opt/taos-pk-workspace")

def server(name, script, env):
    return {"id": f"mcp-{name}-{uuid.uuid4()}", "name": name, "type": "stdio",
            "command": "python3", "args": [f"{bridge}/{script}"], "env": env,
            "enabled": True}

taos = [
    server("taOS_Tank_Fleet", "robotics/tank_fleet_mcp.py",
           {"TAOS_TANK_COORDINATOR_URL": tank_url, "TAOS_TANK_MAX_SPEED": "70"}),
    server("taOS_Cameras", "robotics/camera_mcp.py",
           {"TAOS_CAMERAS_FILE": f"{bridge}/integrations/open-cowork/cameras.json"}),
    server("taOS_TMrFS_Memory", "tmrfs/tmrfs_memory_mcp.py",
           {"TAOS_TMRFS_URL": tmrfs_url, "TAOS_TMRFS_AGENT": "open-cowork"}),
    server("taOS_PK_Trust", "planekey/pk_trust_mcp.py",
           {"PK_VSE_TOOLCHAIN": pk_toolchain, "PK_WORKSPACE": pk_ws}),
]
taos_names = {s["name"] for s in taos}

data = {"servers": []}
if os.path.exists(mcp_path):
    try:
        data = json.load(open(mcp_path))
    except Exception:
        pass
existing = [s for s in data.get("servers", []) if s.get("name") not in taos_names]
data["servers"] = existing + taos  # replace-our-own, keep the rest

os.makedirs(os.path.dirname(mcp_path), exist_ok=True)
json.dump(data, open(mcp_path, "w"), indent=2)
print(f"  {len(taos)} taOS connectors written; {len(existing)} other servers preserved")
PY
echo "  done — restart open-cowork to pick up the connectors."

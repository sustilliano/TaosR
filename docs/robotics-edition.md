# taOS Robotics Edition

Bridges that let taOS agents perceive and act in the physical world:
drive robot fleets and see through IP cameras, entirely on-LAN.

```
┌──────────────────────── taOS controller ────────────────────────┐
│  agent (any framework) ── MCP ──┬── tank-fleet-mcp              │
│                                 └── taos-camera-mcp             │
└───────────────┬─────────────────────────────┬───────────────────┘
                │ REST :8420                  │ HTTP/RTSP
     ┌──────────▼──────────┐        ┌─────────▼──────────┐
     │ tank-agents cluster │        │ Thingino cameras   │
     │ coordinator (Rust)  │        │ (Cinnado D1 etc.)  │
     └──────────┬──────────┘        └────────────────────┘
                │ WebSocket
       ┌────────┴────────┐
       │ TANK-01  TANK-02│  Freenove tanks (Pi 4 / Pi Zero 2W)
       └─────────────────┘
```

Both bridges live in `robotics/` and are **stdlib-only Python** — no pip
installs, so they run on any worker down to a Pi Zero 2W.

## tank-fleet-mcp

Exposes a [tank-agents](https://github.com/sustilliano/claudecode)
cluster coordinator as agent tools:

| Tool | What it does |
|------|--------------|
| `list_tanks` / `fleet_status` | Fleet inventory and coordinator health |
| `drive` | forward/backward/turn with speed clamp; optional `duration_ms` auto-stop |
| `stop` | Single tank, or **fleet-wide emergency stop** when `tank_id` omitted |
| `camera_look` / `camera_capture` | Pan/tilt servos, single-frame capture |
| `led` | Solid/blink/status LED patterns |
| `set_mode` | Manual / Autonomous / Coordinated / Standby / EmergencyStop |
| `autonomy` | Start/stop avoid, explore, follow_person, return_home |

Config: `TAOS_TANK_COORDINATOR_URL` (default `http://localhost:8420`),
`TAOS_TANK_MAX_SPEED` (default 70 — every drive command is clamped to
this, so an agent can never floor it past the fleet limit).

Safety defaults: `stop` sends priority-255 interrupt commands; timed
drives (`duration_ms`) are preferred in the tool description so agents
issue self-terminating movements rather than open-ended ones.

## taos-camera-mcp

Thingino-firmware IP cameras (including Cinnado D1s flashed with
[thingino](https://thingino.com)) as agent tools:

| Tool | What it does |
|------|--------------|
| `list_cameras` | Configured cameras + RTSP URLs (feed these to recorders/detectors) |
| `snapshot` | JPEG snapshot returned inline as an MCP image block — agents see it directly |
| `ptz_move` | Absolute or relative pan/tilt via Thingino's `/ptz` endpoint |

Config: `TAOS_CAMERAS` (inline JSON) or `TAOS_CAMERAS_FILE`
(default `data/cameras.json`):

```json
[
  {"name": "garage", "host": "192.168.1.64"},
  {"name": "porch", "host": "192.168.1.65", "user": "root", "password": "…"}
]
```

## Quickstart

1. Start the tank coordinator on the cluster:
   `TANK_PORT=8420 cargo run --release` (in tank-agents/src/cluster).
2. Install both plugins from the app catalog (`tank-fleet-mcp`,
   `taos-camera-mcp`) and attach them to an agent.
3. Ask the agent: *"check the garage camera, and if anything looks off
   send tank-01 to explore for 30 seconds."*

## Tests

```
pytest tests/robotics/
```

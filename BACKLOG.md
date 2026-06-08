# dcs-bridge — Backlog

## Nomenclature

| Prefix | Meaning |
|--------|---------|
| `FEAT` | Feature — new functionality |
| `BUGF` | Bug fix — correcting a defect |
| `CHOR` | Chore — setup, config, tooling, cleanup |
| `TEST` | Test — unit / integration tests |
| `DOCS` | Documentation — docstrings, README, CHANGELOG |
| `TECH` | Technical — architecture, models, refactoring |
| `RELE` | Release — packaging, versioning, publication |

Ticket IDs are numbered globally per prefix (e.g. `FEAT-001` through `FEAT-036` across all lots).

---

## Summary

| ID | Description | Effort | Status |
|---|---|---|---|
| LOT-001 | Project setup — Poetry + src/ structure | S | ✅ |
| LOT-002 | Shared types — common/ | S | ✅ |
| LOT-003 | Lua bridge script | M | ✅ |
| LOT-004 | dcs-serve core (TCP asyncio + snapshot) | L | ✅ |
| LOT-005 | dcs-serve API (FastAPI + WS + auth) | L | ✅ |
| LOT-006 | dcs-client --tui (Textual) | M | ✅ |
| LOT-007 | dcs-client --mcp (MCP server) | M | ✅ |
| LOT-008 | dcs-client --web (static HTTP + Leaflet) | M | ⬜ |
| LOT-009 | Packaging — PyInstaller + CI GitHub Actions | M | ⬜ |

---

## LOT-001 — Project setup — Poetry + src/ structure

**Status:** ✅ | **Effort:** S

| ID | Description | Status |
|---|---|---|
| CHOR-001 | Initialise `pyproject.toml` with Poetry (dependencies: fastapi, uvicorn, textual, mcp, pydantic, pyyaml) | ✅ |
| CHOR-002 | Create package structure `src/dcs_bridge/serve/`, `client/tui/`, `client/web/static/`, `client/mcp/`, `common/` | ✅ |
| CHOR-003 | Create `test/` directory | ✅ |
| CHOR-004 | Configure ruff, mypy, pytest in `pyproject.toml` | ✅ |
| CHOR-005 | Add `.editorconfig` | ✅ |

---

## LOT-002 — Shared types — common/

**Status:** ✅ | **Effort:** S

| ID | Description | Status |
|---|---|---|
| TECH-001 | Pydantic models: `Unit`, `UnitPositionDcs`, `UnitPositionGeo`, `Command`, `Response`, `DcsEvent`, `FullRefresh` | ✅ |
| TECH-002 | Protocol enums: `CommandAction`, `EventName`, `Coalition` | ✅ |
| TEST-001 | Unit tests for all models | ✅ |

---

## LOT-003 — Lua bridge script

**Status:** ✅ | **Effort:** M

| ID | Description | Status |
|---|---|---|
| FEAT-001 | Outgoing TCP connection to dcs-serve | ✅ |
| FEAT-002 | Exponential backoff reconnect + warning log after N seconds (ADR-0003) | ✅ |
| FEAT-003 | Non-blocking socket (`settimeout(0.0001)`) | ✅ |
| FEAT-004 | Full Refresh every 5 seconds (all units) | ✅ |
| FEAT-005 | Spontaneous events (positions, destructions) | ✅ |
| FEAT-006 | Coordinate conversion via `coord.LOtoLL()` + `land.getHeight()` (ADR-0001) | ✅ |
| FEAT-007 | Execution of received Commands (`exec`, `spawn`) | ✅ |
| FEAT-008 | Injection support via MissionScripting.lua AND DO SCRIPT FILE trigger | ✅ |

---

## LOT-004 — dcs-serve core

**Status:** ✅ | **Effort:** L

| ID | Description | Status |
|---|---|---|
| FEAT-009 | Asyncio TCP handler (listen, accept DCS connection) | ✅ |
| FEAT-010 | Newline-delimited JSON parser | ✅ |
| TECH-003 | In-memory Snapshot (ADR-0002) | ✅ |
| FEAT-011 | Snapshot update via Events + Full Refresh | ✅ |
| FEAT-012 | `ready` / `stale` state management with timestamp | ✅ |
| FEAT-013 | Command/Response correlation by `id` with configurable timeout | ✅ |
| FEAT-014 | DCS disconnection handling (503 / stale) | ✅ |
| TEST-002 | Integration tests with a fake DCS TCP server (pytest fixture) | ✅ |

---

## LOT-005 — dcs-serve API

**Status:** ✅ | **Effort:** L

| ID | Description | Status |
|---|---|---|
| FEAT-015 | `POST /api/exec` with global timeout + per-request override | ✅ |
| FEAT-016 | `POST /api/spawn` | ✅ |
| FEAT-017 | `GET /api/units` (from Snapshot) | ✅ |
| FEAT-018 | `GET /api/mission` | ✅ |
| FEAT-019 | `WS /ws/stream` (delta events + full refresh every 5 s) | ✅ |
| FEAT-020 | API Key middleware (`X-API-Key`) | ✅ |
| FEAT-021 | Automatic key generation on first start | ✅ |
| FEAT-022 | `dcs-serve.yaml` config (loading + defaults) | ✅ |
| FEAT-023 | Correct HTTP codes (200 / 503 / 504 per ADR) | ✅ |
| TEST-003 | FastAPI tests with `httpx.AsyncClient` | ✅ |

---

## LOT-006 — dcs-client --tui

**Status:** ✅ | **Effort:** M

| ID | Description | Status |
|---|---|---|
| FEAT-024 | Unit snapshot display (table) | ✅ |
| FEAT-025 | Arbitrary Lua input + result display | ✅ |
| FEAT-026 | WebSocket connection for real-time updates | ✅ |
| FEAT-027 | `dcs-client.yaml` config | ✅ |

---

## LOT-007 — dcs-client --mcp

**Status:** ✅ | **Effort:** M

| ID | Description | Status |
|---|---|---|
| FEAT-028 | Tool `exec_lua(code, timeout?)` | ✅ |
| FEAT-029 | Tool `get_units()` | ✅ |
| FEAT-030 | Tool `spawn_unit(group_def)` | ✅ |
| FEAT-031 | Tool `get_mission_info()` | ✅ |
| TEST-004 | Unit tests for MCP tools | ✅ |

---

## LOT-008 — dcs-client --web

**Status:** ⬜ | **Effort:** M

| ID | Description | Status |
|---|---|---|
| FEAT-032 | Local static HTTP server (FastAPI StaticFiles) | ⬜ |
| FEAT-033 | Automatic browser open on launch | ⬜ |
| FEAT-034 | Leaflet map with units coloured by coalition | ⬜ |
| FEAT-035 | Hover tooltip (name, type, altitude) | ⬜ |
| FEAT-036 | WebSocket connection for real-time updates | ⬜ |

---

## LOT-009 — Packaging — PyInstaller + CI GitHub Actions

**Status:** ⬜ | **Effort:** M

| ID | Description | Status |
|---|---|---|
| RELE-001 | `dcs-serve.spec` PyInstaller | ⬜ |
| RELE-002 | `dcs-client.spec` PyInstaller | ⬜ |
| RELE-003 | GitHub Actions workflow `release.yml` (build + publish) | ⬜ |
| RELE-004 | PyPI publication | ⬜ |

---

## Ticket Details

### LOT-001 — Project setup

#### CHOR-001 — Initialise `pyproject.toml` with Poetry
Poetry project file declaring all runtime and dev dependencies, ruff/mypy/pytest configuration, and the `dcs-serve` / `dcs-client` entry points.

#### CHOR-002 — Create package structure
`src/dcs_bridge/` with sub-packages `serve/`, `client/tui/`, `client/web/`, `client/mcp/`, `common/`. All packages are importable via `importlib` mode in pytest.

#### CHOR-003 — Create `test/` directory
Empty `test/__init__.py` to mark the directory as a Python package. Test files follow the `test_*.py` naming convention.

#### CHOR-004 — Configure ruff, mypy, pytest
- **ruff**: `line-length = 120`, selects `E`, `F`, `W`, `I`, `UP` rules. `ruff format` is the canonical formatter.
- **mypy**: `check_untyped_defs = true`, `ignore_missing_imports = true`.
- **pytest**: `asyncio_mode = auto`, coverage via `pytest-cov`, `--import-mode=importlib`.

#### CHOR-005 — Add `.editorconfig`
Enforces UTF-8, LF line endings, and 4-space indentation across all contributors.

---

### LOT-002 — Shared types

#### TECH-001 — Pydantic models
All wire-format types shared between the Lua bridge, `dcs-serve`, and the clients. Frozen Pydantic models (`model_config = ConfigDict(frozen=True)`) to enforce immutability after construction. `Response` invariant: exactly one of `result` or `error` must be non-None, enforced via `@model_validator(mode="after")`.

#### TECH-002 — Protocol enums
- `CommandAction`: `exec`, `spawn`.
- `EventName`: `unit_position`, `unit_destroyed`, `unit_spawned`.
- `Coalition`: `IntEnum` (0 = Neutral, 1 = Red, 2 = Blue) matching the DCS scripting API values.
- Protocol: newline-delimited JSON over TCP. Each message is one line ending with `\n`.

#### TEST-001 — Unit tests for all models
Covers valid construction, frozen immutability, `Response` invariant enforcement, and enum value round-trips.

---

### LOT-003 — Lua bridge script

#### FEAT-001 — Outgoing TCP connection
`socket.connect(host, port)` on startup. Non-blocking via `settimeout(0.0001)` to avoid stalling the DCS simulation thread.

#### FEAT-002 — Exponential backoff reconnect
Starts at 1 s, doubles on each failure, capped at 30 s. Logs a warning after 60 s of continuous disconnection (ADR-0003).

#### FEAT-003 — Non-blocking socket
`settimeout(0.0001)` ensures the socket never blocks the simulation thread. The Lua bridge is called by the DCS scheduler on each simulation frame (~20 Hz); any blocking call would freeze the entire simulation. Partial reads are accumulated in a string buffer and flushed line by line when a `\n` delimiter is found.

#### FEAT-004 — Full Refresh every 5 seconds
Serialises all alive units with both DCS-native (`x/y/z`) and geographic (`lat/lon`) coordinates, plus AGL altitude from `land.getHeight()`. Sent as a `full_refresh` JSON message.

#### FEAT-005 — Spontaneous events
`unit_position`, `unit_destroyed`, and `unit_spawned` events pushed to dcs-serve as they occur in the simulation. Registered via DCS event handlers (`world.addEventHandler`). Each event is serialised as a JSON line with `{"type": "<event_name>", "data": {...}}`. Position events include the full `Unit` payload (geo coordinates, AGL altitude, coalition). Destroyed events include only `name`. Spawned events include the full `Unit` payload.

#### FEAT-006 — Coordinate conversion
`coord.LOtoLL()` converts DCS flat-earth coordinates to latitude/longitude. `land.getHeight(x, z)` provides the terrain elevation for AGL calculation (ADR-0001).

#### FEAT-007 — Command execution
- `exec`: runs arbitrary Lua via `load()` and returns the string result.
- `spawn`: calls `coalition.addGroup()` with a group definition table received as JSON.

#### FEAT-008 — Injection modes
- **MissionScripting.lua**: persistent across all missions on the server.
- **DO SCRIPT FILE trigger**: per-mission activation without modifying the DCS installation.

---

### LOT-004 — dcs-serve core

#### FEAT-009 — Asyncio TCP handler
`run_tcp_server()` coroutine: `asyncio.start_server()` on `tcp_host:tcp_port`. Accepts exactly one DCS connection at a time; logs and resets on disconnect.

#### FEAT-010 — Newline-delimited JSON parser
Reads lines from the TCP stream via `asyncio.StreamReader.readline()`. Each line is decoded as UTF-8 and parsed as JSON. Dispatch logic: `full_refresh` and event types (`unit_position`, `unit_destroyed`, `unit_spawned`) go to `Snapshot`; messages with an `id` field go to `CommandBus` as `Response` objects. Malformed JSON lines are logged as warnings and discarded without crashing the handler.

#### TECH-003 — In-memory Snapshot
Replaced atomically on each `full_refresh`. `stale()` returns `True` if the last update is older than `stale_threshold` seconds (ADR-0002).

#### FEAT-011 — Snapshot update via Events + Full Refresh
- `full_refresh`: replaces the internal `dict[str, Unit]` atomically and resets the `last_updated` timestamp.
- `unit_position`: upserts the unit by name with the new position payload.
- `unit_spawned`: inserts the new unit.
- `unit_destroyed`: removes the unit by name; silently ignored if the name is unknown (late event after a prior full refresh).
All mutations go through a single method on `Snapshot` to keep the `last_updated` timestamp consistent.

#### FEAT-012 — `ready` / `stale` state management
Three-state model:
- **Not ready** (`ready = False`): initial state and after DCS disconnects. `GET /api/units` returns 503.
- **Ready** (`ready = True`, `stale() = False`): snapshot is fresh. Normal operation.
- **Stale** (`ready = True`, `stale() = True`): DCS is connected but no update received within `stale_threshold` seconds (default 15 s). `GET /api/units` returns 503 with `{"stale": true}`. Exec commands are still forwarded.

`stale()` is computed as `time.monotonic() - last_updated > threshold` to avoid wall-clock drift.

#### FEAT-013 — Command/Response correlation
`CommandBus`: `register(id)` creates an `asyncio.Event` slot; `wait(id, timeout)` blocks until reply or timeout; `unregister(id)` cleans up on send failure.

#### FEAT-014 — DCS disconnection handling
On TCP disconnect: `DcsConnection.connected` set to `False`, in-flight commands unregistered, snapshot marked stale. API returns 503 until reconnect.

#### TEST-002 — Integration tests with fake DCS TCP server
pytest fixture spins up a real `asyncio` TCP server simulating the Lua bridge. Covers reconnect, stale detection, timeout, and command/response correlation.

---

### LOT-005 — dcs-serve API

#### FEAT-015 — `POST /api/exec`
Forwards Lua code to `CommandBus`, waits for `Response`. Returns 503 if DCS is disconnected, 504 on timeout, 200 with `{"result": ...}` or `{"error": ...}` otherwise.

#### FEAT-016 — `POST /api/spawn`
Sends a `spawn` command with the provided `group_def` dict to the Lua bridge, which calls `coalition.addGroup()`. The `group_def` structure follows the DCS scripting API group definition format (coalition, country, category, units array with position, type, name). Same 503/504/200 status code logic as `FEAT-015`. The Lua bridge returns the spawned group's id as the result string.

#### FEAT-017 — `GET /api/units`
Returns the current Snapshot as a JSON array. Returns 503 if not ready or stale.

#### FEAT-018 — `GET /api/mission`
Executes the following Lua snippet via `FEAT-015`:
```lua
local ok, t = pcall(function() return env.mission.theatre end); return ok and t or 'unknown'
```
Returns `{"result": "<theatre_name>"}` (e.g. `"Caucasus"`, `"Syria"`, `"PersianGulf"`). The `pcall` wrapper prevents a crash if `env.mission` is not yet loaded. Extend this ticket in future lots to return richer mission metadata (start time, weather, blue/red countries).

#### FEAT-019 — `WS /ws/stream`
Authenticates on connect. Sends current snapshot immediately if ready, then subscribes to `EventBroadcaster` and forwards all messages until disconnect.

#### FEAT-020 — API Key middleware
`Depends(_require_api_key)` applied to all HTTP routes. Checks `X-API-Key` header or `api_key` query param.

#### FEAT-021 — Automatic key generation
If `api_key` is absent in `dcs-serve.yaml`, generates a `secrets.token_urlsafe(32)` key and persists it back to the file on first start.

#### FEAT-022 — `dcs-serve.yaml` config
`ServeConfig` Pydantic model with fields: `tcp_host`, `tcp_port`, `http_host`, `http_port`, `api_key`, `default_timeout`, `stale_threshold`.

#### FEAT-023 — Correct HTTP codes
- `200`: success (even if DCS returns a Lua error — the bridge responded).
- `503`: DCS not connected or snapshot stale.
- `504`: command timeout.

#### TEST-003 — FastAPI tests with `httpx.AsyncClient`
ASGI transport via `httpx.AsyncClient`. Covers auth, all endpoints, WS stream, and stale/disconnected states.

---

### LOT-006 — dcs-client --tui

#### FEAT-024 — Unit snapshot display
`DataTable` with columns: Name, Type, Coalition, Lat, Lon, Alt (m). Replaced entirely on each `full_refresh` message from the WebSocket.

#### FEAT-025 — Arbitrary Lua input + result display
`Input` widget submits code via `on_input_submitted`. `POST /api/exec` called via `httpx.AsyncClient`. Result displayed in green, error in red, in a `RichLog` below the input.

#### FEAT-026 — WebSocket connection for real-time updates
`run_worker()` coroutine connecting to `WS /ws/stream`. Reconnects every 5 s on `WebSocketException`. Connection status shown in a docked `Label`.

#### FEAT-027 — `dcs-client.yaml` config
`ClientConfig` Pydantic model (`host`, `port`, `api_key`). `load_config()` falls back to defaults on missing file, invalid YAML, or non-mapping content, with a `logger.warning`. CLI entry point: `dcs-client tui --config <path>`.

---

### LOT-007 — dcs-client --mcp

#### FEAT-028 — Tool `exec_lua(code, timeout?)`
MCP tool signature: `exec_lua(code: str, timeout: float | None = None) -> str`.
Calls `POST /api/exec` with `{"code": code, "timeout": timeout}`. Returns the result string on success. Raises an `McpError` with the DCS error message on failure, 503 (DCS not connected), or 504 (timeout). Intended for AI agents that need to query or mutate the DCS state with arbitrary Lua.

#### FEAT-029 — Tool `get_units()`
MCP tool signature: `get_units() -> list[dict]`.
Calls `GET /api/units`. Returns the full unit list as a list of dicts matching the `Unit` Pydantic schema. Raises `McpError` on 503 (snapshot not ready or stale). Intended to give the AI agent situational awareness of the battlefield.

#### FEAT-030 — Tool `spawn_unit(group_def)`
MCP tool signature: `spawn_unit(group_def: dict) -> str`.
Calls `POST /api/spawn` with the provided `group_def`. Returns the spawned group id on success. The agent is expected to provide a valid DCS group definition dict; no server-side schema validation is performed beyond what `coalition.addGroup()` accepts. Raises `McpError` on 503/504 or Lua error.

#### FEAT-031 — Tool `get_mission_info()`
MCP tool signature: `get_mission_info() -> dict`.
Calls `GET /api/mission`. Returns `{"theatre": "<name>"}`. Intended as a lightweight probe for the agent to orient itself before issuing commands. Extend alongside `FEAT-018` when richer metadata becomes available.

#### TEST-004 — Unit tests for MCP tools
Mock `httpx.AsyncClient` at the transport level to assert: correct URL, correct `X-API-Key` header, correct JSON body per tool. Cover success path, DCS error in response body, 503 → `McpError`, and 504 → `McpError`. Use `pytest-asyncio` with `asyncio_mode = auto`.

---

### LOT-008 — dcs-client --web

#### FEAT-032 — Local static HTTP server
`fastapi.staticfiles.StaticFiles` serving `client/web/static/` on a configurable local port (default 8081 to avoid conflict with dcs-serve on 8080). Uvicorn launched programmatically via `uvicorn.run()` in a thread so the main thread can open the browser. No CORS configuration needed — the page connects to dcs-serve using the full URL including port, not a relative path.

#### FEAT-033 — Automatic browser open
`webbrowser.open(f"http://127.0.0.1:{port}")` called 500 ms after Uvicorn signals readiness (via a threading.Event). Delay avoids opening the browser before the server accepts connections. Falls back gracefully if no browser is available (headless server use case).

#### FEAT-034 — Leaflet map with units coloured by coalition
Single-page HTML/JS app bundled in `client/web/static/`. Uses Leaflet.js from CDN (no build step). DCS theater base layers: OpenStreetMap as default tile provider (no API key required). Each unit rendered as a `L.circleMarker`. Coalition colours: Neutral = `#888`, Red = `#c0392b`, Blue = `#2980b9`. Marker radius scaled by unit category (aircraft larger than ground units).

#### FEAT-035 — Hover tooltip
`L.popup` bound to each marker, content: `<b>{name}</b><br>{type}<br>Alt: {altitude_agl:.0f} m AGL`. Popup opens on hover (`mouseover`), closes on `mouseout`. Clicking a marker pins the popup open until explicitly closed.

#### FEAT-036 — WebSocket connection for real-time updates
JS `WebSocket` connecting to `ws://{host}:{port}/ws/stream?api_key={key}`. On `full_refresh`: clear all markers and re-add from the unit list. On `unit_position` / `unit_spawned`: upsert marker by name. On `unit_destroyed`: remove marker by name. Reconnect with 5 s delay on close or error. Connection state displayed in a status badge in the top-right corner of the map.

---

### LOT-009 — Packaging

#### RELE-001 — `dcs-serve.spec` PyInstaller
One-file executable for `dcs-serve`. Bundles `dcs-serve.yaml` default template and the Lua script as data files.

#### RELE-002 — `dcs-client.spec` PyInstaller
One-file executable for `dcs-client`. Bundles `dcs-client.yaml` default template.

#### RELE-003 — GitHub Actions workflow `release.yml`
Triggered on `v*` tags. Steps: checkout → Poetry install → ruff + mypy + pytest → PyInstaller build (Linux, Windows, macOS via matrix) → upload artifacts → `gh release create`.

#### RELE-004 — PyPI publication
`poetry publish` step in `release.yml`. Allows installation via `pip install dcs-bridge` alongside binary releases.

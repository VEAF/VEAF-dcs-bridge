# dcs-bridge

Generic bridge between DCS World and external consumers — TUI, web map, and AI agents.

📖 **[Full documentation](https://veaf.github.io/dcs-bridge/)**

---

## Architecture

```
DCS World (Lua 5.1)
    │  dcs-bridge.lua — unit positions + events
    │  TCP JSON (port 9999)
    ▼
dcs-serve (Python asyncio)
    │  in-memory snapshot · command bus · X-API-Key auth
    ├─── HTTP REST ──► dcs-client tui   (Textual terminal UI)
    ├─── WebSocket ──► dcs-client web   (Leaflet map, real-time)
    └─── HTTP REST ──► dcs-client mcp   (MCP stdio → AI agents)
```

## Features

- **Lua bridge** — non-blocking, exponential reconnect, full refresh every 5 s, `exec` and `spawn` commands
- **dcs-serve** — asyncio TCP + FastAPI, snapshot with staleness detection, command/response correlation
- **dcs-client tui** — Textual terminal UI: real-time unit table + Lua REPL
- **dcs-client web** — Leaflet map with coalition-coloured markers and hover tooltips
- **dcs-client mcp** — MCP server exposing `exec_lua`, `get_units`, `spawn_unit`, `get_mission_info`
- **Packaged** — one-file Windows executables via PyInstaller, also available on PyPI

## Quick start

```bash
# 1. Start the server (generates API key on first run)
dcs-serve

# 2. Open the real-time web map
dcs-client web

# 3. Or launch the terminal UI
dcs-client tui
```

Download the latest `dcs-bridge-x.y.z.zip` from [Releases](https://github.com/VEAF/dcs-bridge/releases) — it includes `dcs-serve.exe`, `dcs-client.exe`, and `dcs-bridge.lua`.

## Injecting the Lua script

Copy `dcs-bridge.lua` to the DCS server machine and inject it into your mission.
The recommended method is **[VMCT v6](https://veaf.github.io/documentation/dev/)**, the VEAF toolset that automates Lua injection without modifying `MissionScripting.lua`.

See [Prerequisites](https://veaf.github.io/dcs-bridge/guide/prerequisites/) for full instructions.

## License

MIT — © VEAF

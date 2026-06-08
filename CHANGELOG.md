# Changelog

All notable changes to dcs-bridge will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- packaging: `dcs-serve.spec` and `dcs-client.spec` PyInstaller specs producing one-file Windows executables, bundling the Lua script, static web assets, and YAML config templates
- packaging: `dcs-serve.yaml.template` and `dcs-client.yaml.template` default config files shipped alongside the executables
- ci: `release.yml` GitHub Actions workflow — quality gate (ruff, mypy, pytest) + PyInstaller build + GitHub Release archive + PyPI publish on `published-v*` tags
- dcs-client web: `dcs-client web` subcommand serving a Leaflet map (static HTML/JS) on a local HTTP server (default port 8081) with real-time WebSocket updates, coalition-coloured circle markers, hover tooltips, and automatic browser open on startup
- dcs-client MCP server: `dcs-client mcp` subcommand exposing exec_lua, get_units, spawn_unit and get_mission_info as MCP tools over stdio (FastMCP)
- dcs-client TUI: Textual terminal UI with real-time unit table (WebSocket), Lua REPL input, and reconnect loop
- dcs-client config: ClientConfig (Pydantic) loaded from dcs-client.yaml with safe YAML error handling
- dcs-client entry point: `dcs-client tui` Typer subcommand wiring config loading and TUI launch
- dcs-serve API: POST /api/exec, POST /api/spawn, GET /api/units, GET /api/mission, WS /ws/stream, X-API-Key auth, per-request timeout override
- dcs-serve config: ServeConfig (Pydantic) loaded from dcs-serve.yaml, API key auto-generated and persisted on first start, YAML error handling with safe fallback to defaults
- dcs-serve core: DcsConnection (mutable TCP writer wrapper), EventBroadcaster (safe concurrent fan-out via list snapshot), run_tcp_server coroutine, CommandBus.unregister() for safe send-failure cleanup
- dcs-serve entry point: typer CLI wiring TCP server + uvicorn in the same asyncio event loop
- dcs-serve core: Snapshot (in-memory cache, stale detection), CommandBus (async id/response correlation with timeout), TcpHandler (newline-delimited JSON parser)
- Lua bridge script (src/lua/dcs-bridge.lua): TCP connection, exponential backoff reconnect, full refresh every 5s, exec/spawn command handlers, dual coordinate output via coord.LOtoLL()
- Shared Pydantic models: Unit, UnitPositionDcs, UnitPositionGeo, Command, Response, DcsEvent, FullRefresh
- Protocol enums: CommandAction, EventName
- Project setup: Poetry, pyproject.toml, src/dcs_bridge package structure
- Quality toolchain: ruff, mypy, pytest configured
- Entry points: dcs-serve and dcs-client stubs

# Changelog

All notable changes to dcs-bridge will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- dcs-serve API: POST /api/exec, POST /api/spawn, GET /api/units, GET /api/mission, WS /ws/stream, X-API-Key auth, timeout per-request
- dcs-serve core: Snapshot (in-memory cache, stale detection), CommandBus (async id/response correlation with timeout), TcpHandler (newline-delimited JSON parser)
- Lua bridge script (src/lua/dcs-bridge.lua): TCP connection, exponential backoff reconnect, full refresh every 5s, exec/spawn command handlers, dual coordinate output via coord.LOtoLL()
- Shared Pydantic models: Unit, UnitPositionDcs, UnitPositionGeo, Command, Response, DcsEvent, FullRefresh
- Protocol enums: CommandAction, EventName
- Project setup: Poetry, pyproject.toml, src/dcs_bridge package structure
- Quality toolchain: ruff, mypy, pytest configured
- Entry points: dcs-serve and dcs-client stubs

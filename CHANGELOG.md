# Changelog

All notable changes to dcs-bridge will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- chore(packaging): migrate `pyproject.toml` metadata to the PEP 621 `[project]` table (name, version, description, readme, license, authors, requires-python, `[project.urls]`, `[project.scripts]`); dependencies stay Poetry-managed via `dynamic = ["dependencies"]`. Clears all `poetry check` deprecation warnings; the built wheel is unchanged (name, version, `Requires-Dist`, and both console-script entry points verified) (LOT-014)
- chore(backlog): migrate the monolithic `BACKLOG.md` to a per-lot `.backlog/` structure (active lots as directories, completed lots compacted under `.backlog/archive/`); wire the Matt Pocock skills via `docs/agents/*` and an `## Agent skills` block in `CLAUDE.md` (ADR-0004)

### Fixed
- fix(ci): `python-quality` now always runs (dropped the workflow-level `paths` filter) and gates the heavy steps (ruff/mypy/pytest) internally via a `dorny/paths-filter` step. A doc-only or backlog-only PR still produces the required `python-quality` status (green, checks skipped) instead of leaving it permanently pending and blocking the merge (LOT-019)
- fix(web): `dcs-client web` now applies the configured serve `host`/`port`/`api_key`. The web server exposes them at `GET /config.json` and the Leaflet page reads it at startup (URL hash still honoured as an override), so a filled `dcs-client.yaml` connects the map automatically instead of falling back to empty credentials and being rejected by `dcs-serve` (`/ws/stream` code 4001). Docs updated + security note on the local api_key exposure (LOT-015)
- fix(web): vendor Leaflet 1.9.4 locally (`static/vendor/leaflet/`) instead of loading it from the `unpkg.com` CDN. The CDN `leaflet.js` `integrity` hash was corrupted, so browsers rejected the script (`L is not defined`) and the map never rendered; serving the library locally fixes it and removes the external-CDN dependency. Vendored files verified against the official Leaflet SRI hashes (LOT-016)
- fix(lua): reconcile the default TCP port — `dcs-bridge.lua` now defaults to `7777`, matching `ServeConfig.tcp_port` and `dcs-serve.yaml.template`; all documentation examples (configuration, prerequisites, quickstart, architecture — EN + FR) aligned from the stale `9999` to `7777`. A fresh docs-driven setup now connects without a manual port override (LOT-013 / ticket 01)
- feat(lua): the reconnect warning now appends the connection target `(target: <host>:<port>)`, so a port/host mismatch is visible in DCS.log instead of manifesting as silence (LOT-013 / ticket 02)
- fix(packaging): add missing `[build-system]` table to `pyproject.toml` (poetry-core backend) — PEP 517 installers (`pip`/`pipx`/`uv`, `pip install git+...`) no longer fall back to setuptools and produce a nameless `UNKNOWN-0.0.0` wheel without console-script entry points (LOT-012)
- fix(serve): separate Typer command function from Poetry entry point — prevents `TypeError: 'bool' object is not callable` when `dcs-serve` was invoked directly (LOT-011 / BUGF-001)
- fix(client): replace `typer.Option(Path(...))` with `typer.Option(default=...)` in all three subcommands to prevent the same Typer OptionInfo-as-default bug (LOT-011 / BUGF-002)

### Added
- docs: MkDocs + GitHub Pages setup — mkdocs-material, mkdocs-static-i18n (suffix mode, FR/EN), mike versioned docs; docs group in pyproject.toml
- docs: GitHub Actions workflow docs.yml — deploys to gh-pages on push to develop (alias dev) and master (alias latest) via mike
- docs: user documentation in FR and EN — prerequisites, installation, configuration, quick start, CLI reference
- docs: technical documentation in FR and EN — architecture (Mermaid diagram), wire protocol, contributing guide (TDD, Conventional Commits, Git Flow), REST + WebSocket API reference
- docs: README.md rewrite — pitch, ASCII architecture diagram, feature list, 3-command quick start, link to GitHub Pages, VMCT v6 note

### Added
- packaging: `dcs-serve.spec` and `dcs-client.spec` PyInstaller specs producing one-file Windows executables, bundling the Lua script, static web assets, and YAML config templates
- packaging: `dcs-serve.yaml.template` and `dcs-client.yaml.template` default config files shipped alongside the executables
- ci: `release.yml` GitHub Actions workflow — quality gate (ruff, mypy, pytest) + PyInstaller build + GitHub Release archive on `published-v*` tags
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

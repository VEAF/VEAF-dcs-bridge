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
- feat(serve): role-based security — roles, tokens, per-action enforcement (ADR-0005 / LOT-018 ticket 06) — new `serve/security.py` with roles `observer(0)/pilot(1)/operator(10)/administrator(90)/superuser(99)` aligned on VEAF levels, and a role-bearing token store (`{token, role, label, ucid?, expiry?}`, loaded from `dcs-tokens.yaml`) that replaces the single API key. Enforcement lives in the bridge: each action's minimum role is checked before execution (`403` below minimum), `POST /api/exec` is gated to `superuser`, read-only routes to `observer`, `/api/spawn` to `operator`. The caller's resolved VEAF level is propagated into VEAF-backed adapters (never a blanket `bypassSecurity`). Delegated WEB mode resolves UCID→role from `veaf-pilots.txt` server-side. The legacy `api_key` keeps working as a `superuser` token during the transition. API reference updated (EN + FR)
- feat(serve): VEAF/VMCT backend (ADR-0005 / LOT-018 ticket 05) — a VEAF adapter drives `veafCommands.execute(pos, text, coalition, nil, nil)`, composing the marker keyphrase per module grammar (no typed per-field VEAF API) and running it without a map marker or blanket security bypass. New `run_keyphrase` verb (arbitrary VEAF keyphrase + optional params); `spawn` gains a VEAF backend for `farp`/`fob` (preferred over CTLD/DCS when VMCT is present). The VMCT default shortcut list is catalogued (`veaf_shortcuts`) and discoverable via `search_catalog`; per-mission custom aliases stay out of scope. Role→VEAF-level propagation is wired in ticket 06
- feat(serve): MIST & CTLD backends + hybrid backend preference (ADR-0005 / LOT-018 ticket 04) — `spawn` now has three backends: DCS-native (`coalition.addGroup` for units, `coalition.addStaticObject` for `farp`/`fob`), MIST (`mist.dynAdd`, unit kinds), and CTLD v2 (`CTLDSceneManager:playSceneAtPos` for `farp`/`fob`). Backend selection follows the global preference `VMCT > CTLD > MIST > DCS`, filtered by detected capabilities and by the `kind` each backend handles (a vehicle prefers MIST→DCS, a FARP prefers CTLD→DCS static); an optional `backend=` forces one (debug/repro). Added `farp`/`fob` spawn kinds
- feat(serve): action catalogue + parameterised verbs + discovery (ADR-0005 / LOT-018 ticket 03) — the action registry now declares per-action arg schema (`ParamSpec`), supported backends + preference, minimum role (placeholder until ticket 06) and portable/specific scope. Added DCS-native `smoke` (coloured marker) and `remove` (destroy group by name) verbs alongside `spawn`; the long tail of parameter values (DCS unit types) lives as queryable data (`serve/catalog.py`), not as tools. New endpoints `GET /api/catalog` (union filtered by detected capabilities), `GET /api/catalog/search?q=` and `GET /api/catalog/{name}` (describe, resolving long-tail values). API reference updated (EN + FR)
- feat(serve): capability detection (ADR-0005 / LOT-018 ticket 02) — the Lua bridge announces the loaded frameworks and versions (`mist`/`ctld`/`veaf`, DCS implicit) at the handshake on every (re)connect; serve matches each against the version this build targets (version **lockstep**, equality — a mismatch marks the capability absent with a logged reason), caches the set, clears it on disconnect, and exposes it at `GET /api/capabilities`. New `serve/capabilities.py`; API reference updated (EN + FR)
- feat(serve): capability-aware bridge tracer-bullet — semantic `spawn` action end-to-end via a DCS-native backend (ADR-0005 / LOT-018 ticket 01). New `POST /api/action {name, args, backend?}` routes a high-level verb to a backend adapter; the `spawn` adapter emits `coalition.addGroup(...)` with **no MIST dependency**, replacing the MIST-only `/api/spawn` limitation. Adds a Python→Lua serialiser (`serve/lua.py`, centralised string escaping) and an action registry (`serve/actions.py`). The MCP client gains a semantic `spawn` tool calling `/api/action`. API reference updated (EN + FR)
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

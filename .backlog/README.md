# Backlog — dcs-bridge

Per-lot backlog. Active lots are directories under `.backlog/<LOT-ID>/` (a `PRD.md`
plus one `tickets/<NN>-<slug>.md` per ticket); completed lots are compacted into
`.backlog/archive/<LOT-ID>.md` (ticket table preserved). This index is the source of
truth for **scope and status**.

`.backlog/` is internal working state (a dotfolder, excluded from the published
MkDocs site). See [`docs/agents/issue-tracker.md`](../docs/agents/issue-tracker.md)
for the conventions that skills read at runtime.

## Legend

- **Status**: ⬜ ready · 🔄 in-progress · 🧑 waiting-human · ✅ done · 🚫 wontfix

## Active lots

| Lot | Status |
|-----|--------|
| [LOT-012](LOT-012/PRD.md) — Fix missing `[build-system]` in pyproject.toml (blocks `pip`/`pipx install`, produces `UNKNOWN-0.0.0` with no entry points) | ✅ done |
| [LOT-013](LOT-013/PRD.md) — Reconcile default TCP port across dcs-bridge.lua (9001), dcs-serve (7777), and docs (9999) — silent connection failure, no error anywhere | ✅ done |
| [LOT-014](LOT-014/PRD.md) — Migrate pyproject.toml metadata to PEP 621 `[project]` table (clears `poetry check` deprecation warnings) | ✅ done |
| [LOT-015](LOT-015/PRD.md) — `dcs-client web` must apply the configured serve host/port/api_key (map stuck "Disconnected" out of the box; config file has no effect) | ✅ done |
| [LOT-016](LOT-016/PRD.md) — Vendor Leaflet locally in the web client (corrupted CDN SRI hash broke the map with `L is not defined`) | ✅ done |
| [LOT-017](LOT-017/PRD.md) — MCP tool errors are not actionable: the client reads only the `error` body key, so every `401`/`403` (which dcs-serve reports under `detail`) lost its explanation and read `dcs-serve returned 401: 401`; `401` and `403` now get opposite advice (credential vs role), an unreachable dcs-serve no longer raises, and the client's 5 s httpx default no longer expires before the server's 10 s | ✅ done |
| [LOT-018](LOT-018/PRD.md) — Implement the capability-aware bridge (ADR-0005): semantic-action façade over DCS/MIST/CTLD/VMCT, capability detection, role-based security | ✅ done |
| [LOT-019](LOT-019/PRD.md) — Doc-only PRs blocked by the required `python-quality` check (paths filter never fires it) | ✅ done |
| [LOT-020](LOT-020/PRD.md) — Packaged `dcs-serve.exe` exits instantly doing nothing (`dcs-serve.spec` freezes `serve/app.py` as the script, but that module has no `__main__` guard, so `main()` is never called — the Poetry console-script masked it); fix applied locally, needs commit + a CI smoke test that the built exe actually listens. Then publish the **first** release (**v1.0.0**), so `dcs-bridge-<version>.zip` (with `dcs-serve.exe`) becomes downloadable — VMCT's new map-capture-kit job depends on it. Also documents the mandatory `MissionScripting.lua` sanitisation lift, which was missing from the prerequisites | ✅ done |

## Archived lots

| Lot | Status |
|-----|--------|
| [LOT-001](archive/LOT-001.md) — Project setup (Poetry + src/ structure) | ✅ |
| [LOT-002](archive/LOT-002.md) — Shared types (common/) | ✅ |
| [LOT-003](archive/LOT-003.md) — Lua bridge script | ✅ |
| [LOT-004](archive/LOT-004.md) — dcs-serve core (TCP asyncio + snapshot) | ✅ |
| [LOT-005](archive/LOT-005.md) — dcs-serve API (FastAPI + WS + auth) | ✅ |
| [LOT-006](archive/LOT-006.md) — dcs-client --tui (Textual) | ✅ |
| [LOT-007](archive/LOT-007.md) — dcs-client --mcp (MCP server) | ✅ |
| [LOT-008](archive/LOT-008.md) — dcs-client --web (static HTTP + Leaflet) | ✅ |
| [LOT-009](archive/LOT-009.md) — Packaging (PyInstaller + CI GitHub Actions) | ✅ |
| [LOT-010](archive/LOT-010.md) — Documentation (MkDocs + GitHub Pages) | ✅ |
| [LOT-011](archive/LOT-011.md) — Typer entry-point fixes | ✅ |

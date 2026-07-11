# 01 — Tracer-bullet: semantic `spawn` end-to-end via the DCS-native backend

Status: 🔄 in-progress
Type: feat

Ref: [ADR-0005](../../../docs/adr/0005-capability-aware-bridge.md) — decisions *Shape*, *Placement*, *Execution*.

## What to build

The thinnest vertical slice that proves the façade and already removes the MIST-only
`spawn` limitation:

- **serve**: a minimal action registry holding one action (`spawn`) with one backend
  adapter (`dcs`); a `POST /api/action {name, args}` endpoint that routes to the adapter.
- **adapter (Python→Lua)**: `spawn` DCS-native adapter emitting `coalition.addGroup(...)`
  via a small Python→Lua serialiser (positions, escaped strings, tables).
- **Lua**: execute the generated snippet (reuse the existing exec channel; no routing in
  Lua).
- **client**: expose `spawn` through the MCP client as one tool that calls `/api/action`.

Hard-code capability = DCS-only for this slice (real detection is ticket 02). No catalogue
filtering, no security yet (reuse current auth).

## Acceptance criteria

- [ ] `POST /api/action {name:"spawn", args:{kind:"vehicle", type:"Hummer", position, coalition}}`
      spawns the unit in DCS with no MIST dependency.
- [ ] The MCP `spawn` tool performs the same end-to-end against a running mission.
- [ ] Python→Lua serialiser unit-tested (positions, string escaping, nested tables);
      adapter output asserted. Quality gate green.

## Blocked by
None.

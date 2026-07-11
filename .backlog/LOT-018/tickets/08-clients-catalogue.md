# 08 — Clients: MCP catalogue mapping, TUI/WEB presentation

Status: ⬜ ready
Type: feat

Ref: [ADR-0005](../../../docs/adr/0005-capability-aware-bridge.md) — decisions *Granularity*, *Placement*.

## What to build

- **MCP**: expose the handful of parameterised verbs + `search_catalog`/`describe`; no
  domain knowledge in the client — it proxies `/api/action` and the catalogue.
- **TUI/WEB**: present the capability-filtered catalogue (available actions for the running
  mission) and issue actions through the generic API.
- Retire the ad-hoc `exec_lua`/`spawn`/`get_units`/`get_mission` MCP tools in favour of the
  catalogue-driven verbs (keep `exec_lua` as a `superuser` verb).

## Acceptance criteria

- [ ] MCP tool count stays small (verbs + discovery), independent of catalogue size.
- [ ] TUI/WEB show only actions available for the current mission's capabilities.
- [ ] Quality gate green.

## Blocked by
Tickets 03, 06 (catalogue + roles).

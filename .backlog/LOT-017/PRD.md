# Lot LOT-017 — MCP tools report misleading errors for non-200 responses

Status: ⬜ ready

**Effort**: S
**Branch**: (not started)

## Problem Statement

Every MCP tool in `src/dcs_bridge/client/mcp/server.py` collapses **any** non-200
response from dcs-serve into the same string:

```python
if resp.status_code != 200:
    return f"Error: dcs-serve returned {resp.status_code} — DCS not ready"
```

So a `401` (wrong/missing `api_key`) is reported as *"DCS not ready"*, which points the
user at DCS or the bridge process when the real cause is authentication. This was hit
live (2026-07-11) while wiring the MCP server into Claude Desktop: a config/key mismatch
surfaced as "DCS not ready", costing debugging time before the `401` was noticed.

Related gap: if dcs-serve is not reachable at all (process down), the `httpx` call
raises `ConnectError` — currently unhandled, so the tool fails with a raw exception
instead of a clear message.

## Solution

Map the failure to an actionable message in all four tools (`exec_lua`, `get_units`,
`spawn_unit`, `get_mission_info`), ideally via a shared helper:

- `401` / `403` → authentication error: "api_key rejected — check it matches
  dcs-serve.yaml".
- `502` / `503` / `504` (and the documented "DCS not ready" server path) → keep the
  DCS-not-ready wording.
- other non-200 → include the status code and any server-provided detail.
- `httpx.ConnectError` / timeout → "cannot reach dcs-serve at <host>:<port>".

Keep the return contract unchanged (string for exec/spawn/mission, dict-with-`error`
for get_units).

## User Stories

1. As someone wiring the MCP server into a client, I want a `401` to say the api_key is
   wrong, so I fix the key instead of hunting a non-existent DCS problem.
2. As a user whose dcs-serve is down, I want a clear "cannot reach dcs-serve" message
   rather than a raw stack trace.

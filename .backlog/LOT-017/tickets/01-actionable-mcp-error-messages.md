# 01 — Distinguish auth / unreachable / DCS-not-ready in MCP tool errors

Status: ⬜ ready
Type: fix

## What to build

In `src/dcs_bridge/client/mcp/server.py`, replace the four identical
`f"...returned {status} — DCS not ready"` branches with an actionable mapping,
factored into a shared helper (e.g. `_error_message(resp) -> str`):

- `401` / `403` → `"api_key rejected (HTTP {status}) — check it matches dcs-serve.yaml"`.
- `502` / `503` / `504` → keep the DCS-not-ready wording.
- other non-200 → `"dcs-serve returned {status}"` plus any server-provided detail.

Wrap the `httpx` calls so `httpx.ConnectError` / `httpx.TimeoutException` return a clear
`"cannot reach dcs-serve at {host}:{port}"` instead of raising.

Preserve return types: `exec_lua` / `spawn_unit` / `get_mission_info` return the string;
`get_units` returns `{"error": <message>}`.

## Acceptance criteria

- [ ] A `401` from dcs-serve yields a message mentioning the api_key, not "DCS not ready".
- [ ] `502/503/504` still yield the DCS-not-ready message.
- [ ] With dcs-serve down, each tool returns a "cannot reach dcs-serve" message (no raw
      exception surfaced to the MCP client).
- [ ] Return types unchanged (string vs `{"error": ...}` for get_units).
- [ ] Unit tests cover the 401, 503, generic non-200 and connection-error paths
      (mock httpx responses / raise). Quality gate green (ruff, mypy, pytest).

## Blocked by

None.

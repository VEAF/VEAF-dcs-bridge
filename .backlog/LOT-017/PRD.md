# Lot LOT-017 — MCP tools report misleading errors for non-200 responses

Status: ✅ done

**Effort**: S
**Branch**: `fix/LOT-017`

## Problem Statement

> **Historical — written 2026-07-11, before LOT-018.** Kept for the original motivation;
> the code it describes no longer exists. See the re-scoping note under *Solution* and the
> comparison table in [ticket 01](tickets/01-actionable-mcp-error-messages.md).

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

> **Re-scoped 2026-07-28.** The problem statement above predates LOT-018, which rewrote
> the MCP client: the literal `"DCS not ready"` string no longer exists, the shared helper
> already exists (`_unwrap`), and `spawn_unit`/`get_mission_info` were retired. Two *real*
> defects were found in its place, plus a third while investigating. See
> [ticket 01](tickets/01-actionable-mcp-error-messages.md) for the full comparison.

## Solution

| # | Ticket | Status |
|---|--------|--------|
| 01 | [Distinguish auth / role / unreachable / DCS-not-ready](tickets/01-actionable-mcp-error-messages.md) — the client discards the server's own explanation (it reads only `error`, while `401`/`403` put it in `detail`), and `401` vs `403` need opposite advice | ✅ |
| 02 | [The client's 5 s httpx default is shorter than the server's 10 s](tickets/02-client-timeout-shorter-than-server.md), so slow commands time out client-side and blame DCS — and `exec_lua(timeout=…)` cannot work | ✅ |

## User Stories

1. As someone wiring the MCP server into a client, I want a `401` to name the credential
   and a `403` to name the *role*, so I fix the right thing — changing the key when the
   role is too low is wasted effort.
2. As a user whose dcs-serve is down, I want a clear "cannot reach dcs-serve" message
   rather than a raw stack trace.
3. As an agent issuing a slow DCS command, I want the server's own verdict, not a
   client-side cutoff that misattributes the delay.

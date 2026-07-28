# 01 — Distinguish auth / role / unreachable / DCS-not-ready in MCP tool errors

Status: ✅ done
Type: fix

## ⚠️ This ticket was written before LOT-018 — re-scoped

The PRD's premise is **stale**. Checked against the code on 2026-07-28:

| Original assumption | Reality |
|---|---|
| Four identical `"…returned {status} — DCS not ready"` branches | **Gone.** LOT-018 #08 rewrote the MCP client; `"DCS not ready"` no longer appears anywhere in `src/`. |
| Factor the mapping into a shared helper | **Already done** — every tool goes through `_get`/`_post` → `_unwrap`. |
| Tools `spawn_unit` / `get_mission_info` | **Retired** by LOT-018 #08 in favour of catalogue discovery + `run_action`. Seven tools now. |
| `401`/`403` → "api_key rejected — check it matches dcs-serve.yaml" | **Wrong now.** ADR-0005 made these two different failures (below), and credentials moved to `dcs-tokens.yaml`. |

Two real defects remain, and they are worth more than the original wording change.

### Defect A — the client discards the server's own explanation

dcs-serve reports errors in **two different body shapes**, and `_unwrap` reads only one:

| Source | Status | Body |
|---|---|---|
| `_resolve_token` (`HTTPException`) | 401 | `{"detail": "Invalid or missing token"}` |
| `require_role` dependency (`HTTPException`) | 403 | `{"detail": "role observer below required operator"}` |
| `/api/action` per-action check (`JSONResponse`) | 403 | `{"error": "role … below required …"}` |
| `/api/action` bad args, unknown action, timeout | 400/404/504 | `{"error": …}` |
| DCS not connected / stale snapshot | 503 | `{"ready": false}` — no message at all |

`_unwrap` does `resp.json().get("error", detail)` with `detail` defaulting to the **status
code integer**. So for every `HTTPException` path the server's explanation is thrown away
and the user gets `dcs-serve returned 401: 401` — the status twice and nothing actionable.
The information already exists server-side; the client drops it.

### Defect B — `401` and `403` are not the same problem

Post-ADR-0005 they need opposite advice, so the original ticket's single message would
itself have been misleading:

- **401** — the token is unknown, missing or expired. Fix the credential: it must match an
  entry in dcs-serve's `dcs-tokens.yaml`, or the legacy `api_key` in `dcs-serve.yaml`
  (still accepted as a `superuser` token).
- **403** — the token is **valid**; its *role* is below what the action requires. Changing
  the key is the wrong move; a higher-role token is needed.

### Also still true from the original ticket

`httpx.ConnectError` / `httpx.TimeoutException` are unhandled, so a dcs-serve that is down
surfaces a raw exception to the MCP client.

## What to build

In `src/dcs_bridge/client/mcp/server.py`:

- Read the server's explanation from **both** `detail` and `error` keys, and stop
  defaulting it to the status code.
- Map each status to advice that names the actual fix: 400 (arguments → `describe_action`),
  401 (credential), 403 (role, explicitly *not* the credential), 404 (unknown action →
  `list_catalog`), 502/503/504 (DCS not ready / timeout).
- Catch `httpx.TimeoutException` then `httpx.RequestError` (`ConnectError` is a subclass)
  and return `"cannot reach dcs-serve at {host}:{port}"` rather than raising.

Preserve return types: `run_action` / `exec_lua` return the string, everything else
returns parsed JSON or `{"error": <message>}`.

## Acceptance criteria

- [x] A `401` names the credential and points at `dcs-tokens.yaml`, and carries the
      server's `"Invalid or missing token"` instead of discarding it.
- [x] A `403` says the **role** is insufficient and states it is not a wrong key — for
      both body shapes (`detail` from the dependency, `error` from `/api/action`).
- [x] `502/503/504` still say DCS is not ready, and `504` is identified as a timeout.
- [x] `400`/`404` point at `describe_action` / `list_catalog`.
- [x] No message contains the status code twice.
- [x] A non-JSON error body degrades to the status alone without raising.
- [x] With dcs-serve down, every tool returns a "cannot reach dcs-serve at host:port"
      message — no raw exception reaches the MCP client.
- [x] Return types unchanged (string for `run_action`/`exec_lua`, `{"error": …}` otherwise).
- [x] Unit tests cover each status above, both body shapes, the non-JSON body, and the
      connect/timeout paths. Quality gate green (ruff, mypy, pytest).

## Blocked by

None.

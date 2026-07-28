# 02 — The MCP client gives up before dcs-serve does, so timeouts blame the wrong thing

Status: ✅ done
Type: fix

## Problem

`DcsMcpServer` builds `httpx.AsyncClient()` with no `timeout`, so it uses httpx's default
of **5.0 s** (verified: httpx 0.28.1, `httpx.Client().timeout` → `Timeout(timeout=5.0)`).

dcs-serve's own patience is **`ServeConfig.default_timeout = 10.0 s`**, and `/api/exec`
accepts a per-request `timeout` override that can be larger still.

So for any DCS command taking between 5 and 10 seconds, the **client** aborts first while
the server is still legitimately waiting. Worse, `exec_lua(code, timeout=30)` is a
documented parameter that cannot work: the caller asks the server for 30 s of patience and
the client hangs up after 5.

This lands squarely in this lot: a client-side cutoff reported as a timeout misattributes
the cause to DCS, which is the exact failure mode LOT-017 exists to remove. Fixing the
message in ticket 01 while leaving this would produce an *accurately worded* lie.

## Why it went unnoticed

Every existing test mocks `httpx.AsyncClient`, so no test ever exercises a real timeout,
and interactive use has so far involved fast commands.

## Fix

Give the client a timeout strictly greater than the server's, so the **server's** 504
(`{"error": "timeout"}`) is what surfaces — it is the authoritative, accurate answer.

- A module-level default comfortably above `ServeConfig.default_timeout`.
- When a caller passes an explicit `timeout` to `exec_lua`, derive the client timeout from
  it (requested + margin) so the override actually works.

Deliberately **not** adding a `timeout` field to `ClientConfig`: the client cannot know the
server's configured `default_timeout` anyway, and the point is only to stop the client from
being the first to give up (RULE N°2 — no speculative configuration surface).

## Acceptance criteria

- [x] `httpx.AsyncClient` is constructed with an explicit timeout greater than
      `ServeConfig.default_timeout`.
- [x] `exec_lua(code, timeout=T)` uses a client timeout greater than `T`.
- [x] Unit tests assert the timeout actually passed to `httpx.AsyncClient`, including the
      derived-from-override case — the gap existed because nothing checked this.

## Blocked by

None. Shares a branch with ticket 01 (same file, same lot).

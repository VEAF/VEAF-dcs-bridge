# Lot LOT-013 — Reconcile the default TCP port across dcs-bridge.lua, dcs-serve, and docs

Status: ✅ done

**Effort**: XS
**Branch**: fix/lot-013

## Problem Statement

The Lua bridge script and the Python service disagree on the default TCP port, and the
published docs disagree with both:

| Source | Default TCP port |
|---|---|
| `src/lua/dcs-bridge.lua` (`dcsBridge.port` default, line ~18/35) | **9001** |
| `src/dcs_bridge/serve/config.py` (`ServeConfig.tcp_port` default) | **7777** |
| `dcs-serve.yaml.template` (`tcp_port` example value) | 7777 (matches the code default) |
| `docs/guide/quickstart.en.md` (example log output) | **9999** |

None of these three values match. In practice this means: if a user follows the mission-side
setup instructions (`docs/guide/prerequisites.md`, Method B) without *also* explicitly setting
`dcsBridge.port` to match their actual `dcs-serve.yaml` `tcp_port`, the Lua bridge silently
tries to connect on port 9001 while `dcs-serve` listens on 7777 (or whatever the user's yaml
says) — the TCP connection never establishes, and there is **no error anywhere**: `dcs-serve`'s
console simply never prints "DCS connected", and there is nothing in DCS's own log pointing at
a port mismatch either (reproduced 2026-07-10 on a CTLD project consumer machine — cost real
debugging time to trace back to this).

## Solution

Pick ONE canonical default port (recommend keeping `7777`, since it's already the `ServeConfig`
code default and matches the shipped `.yaml.template`), and:

1. Update `src/lua/dcs-bridge.lua`'s `dcsBridge.port` default (both the header comment example
   and the actual runtime default assignment) to match.
2. Fix `docs/guide/quickstart.en.md`'s example log output to show the real default instead of
   9999 (and its `.fr.md` counterpart if it has the same example).
3. Consider making the mismatch impossible to miss silently going forward: either (a) have
   `dcs-bridge.lua` log a clear warning at startup showing which host/port it's about to try
   (so a mismatch is visible in DCS's log immediately rather than only manifesting as "nothing
   happens"), and/or (b) have `dcs-serve` log the expected port prominently at every startup
   (it already does — `TCP server listening on (...)` — this part is fine, the gap is purely on
   the Lua side never announcing what it's attempting to connect to).

## User Stories

1. As someone setting up dcs-bridge for the first time, I want the Lua bridge's default port to
   match `dcs-serve`'s default, so that a fresh setup following the docs works without needing
   to discover an undocumented mismatch.
2. As someone whose mission-side `dcsBridge` config doesn't match `dcs-serve`, I want the Lua
   bridge to log what it's trying to connect to, so a port mismatch is visible in DCS's log
   instead of manifesting as total silence.

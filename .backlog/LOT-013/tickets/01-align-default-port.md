# 01 — Align dcs-bridge.lua's default port with dcs-serve's

Status: ✅ done
Type: fix

## What to build

In `src/lua/dcs-bridge.lua`:
- Change the header comment example (`dcsBridge.port = 9001`, ~2 occurrences in the docstring)
  and the actual runtime default (`dcsBridge.port = dcsBridge.port or 9001`) to **7777**, matching
  `ServeConfig.tcp_port`'s default in `src/dcs_bridge/serve/config.py` and
  `dcs-serve.yaml.template`.

In `docs/guide/quickstart.en.md` (and `.fr.md` if it repeats the example): fix the illustrative
log output showing port **9999** to show the real default (7777) instead.

## Acceptance criteria

- [x] `dcsBridge.port` default in `dcs-bridge.lua` is `7777` (comment + code, both updated).
- [x] Quickstart doc's example log line shows a port matching the actual code default.
      Scope extended: all doc `9999` occurrences aligned to `7777` (configuration, prerequisites,
      quickstart, architecture — EN + FR), since the mismatch was repo-wide, not just quickstart.
- [x] A fresh setup following the docs with zero manual `dcsBridge` port override connects
      successfully (Lua default now `7777` == `ServeConfig.tcp_port` default, verified by
      `test_serve_config.py`).

## Blocked by

None.

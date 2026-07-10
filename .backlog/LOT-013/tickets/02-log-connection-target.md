# 02 — Log the connection target so a mismatch is visible

Status: 🔄 in-progress
Type: feat

## What to build

`dcs-bridge.lua` already warns after `reconnectWarnAfter` seconds of failed connection
(`tryConnect()`, ~line 216-221):

```lua
logWarning(string.format(
    "no connection for %ds — retrying every %ds (max backoff %ds)",
    math.floor(disconnectedFor), _backoff, dcsBridge.reconnectBackoffMax
))
```

This message never states *what host/port it's trying to reach* — so a port/host
misconfiguration (e.g. `dcsBridge.port` left at its default while `dcs-serve` listens on a
different port) produces a warning that gives no actionable clue. Add the target to both:

- The initial startup log (log once at load time: `"connecting to <host>:<port>"`).
- The existing disconnect warning: append `" (target: <host>:<port>)"` or similar.

## Acceptance criteria

- [x] DCS.log shows the exact `host:port` dcs-bridge.lua is attempting, both at script load and
      in the reconnect-warning message. Note: the startup log (`initializing — connecting to
      %s:%d`) already existed; only the reconnect warning was missing the target — appended
      `(target: %s:%d)`.
- [x] No change to reconnect timing/backoff behavior — logging only.

## Blocked by

None — independent of ticket 01, can land in the same lot/PR.

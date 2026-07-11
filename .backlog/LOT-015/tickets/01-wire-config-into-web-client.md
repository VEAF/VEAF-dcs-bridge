# 01 — Wire serve host/port/api_key into the web client

Status: ✅ done
Type: fix

## What to build

Make `dcs-client web` deliver the configured serve target to the Leaflet page so a
filled `dcs-client.yaml` connects the map with no manual URL hash.

Preferred approach (B — served config endpoint):

- `run_web(...)` gains the serve `host`, `port`, `api_key` params (from `ClientConfig`);
  `web()` in `app.py` passes `cfg.host` / `cfg.port` / `cfg.api_key` through.
- The web `FastAPI` app exposes `GET /config.json` returning `{host, port, api_key}`
  (mounted alongside the existing `StaticFiles`; make sure the static mount at `/` does
  not shadow the route — mount static last or under a subpath).
- `index.html` fetches `/config.json` at startup and uses it for the WebSocket URL,
  falling back to the URL hash then to the current defaults if the fetch fails.
- Keep the browser-open URL clean (`http://<web_host>:<web_port>`), no hash needed.

Acceptable minimal alternative (A — hash injection): `run_web` opens the browser at
`.../#host=…&port=…&api_key=…`. Document which was chosen in the PR.

## Acceptance criteria

- [x] With a `dcs-client.yaml` pointing at a dcs-serve that has a non-empty `api_key`,
      running `dcs-client web` connects the map with no manual URL editing. Verified in
      the internal preview pane: the page reads `/config.json` and the reconnect attempt
      targets `ws://127.0.0.1:8080/ws/stream?api_key=test-key-123` (config values, not
      defaults).
- [x] Wrong/empty `api_key` still yields a visible "Disconnected" state (failure path
      unchanged; only the source of the credentials changed).
- [x] `--web-host` / `--web-port` CLI overrides still work (covered by
      `test_web_command_web_port_override_wins`).
- [x] Unit tests: `web()` forwards the config's host/port/api_key; `/config.json`
      (approach B) returns the configured values; route does not shadow static. Quality
      gate green (ruff, mypy, pytest).

## Security note

Approach B exposes the api_key on an unauthenticated local endpoint. Keep the web
server bound to `127.0.0.1` by default (it already is) and note the exposure in the
docs so users don't bind `--web-host 0.0.0.0` on an untrusted network without
understanding the implication.

## Blocked by

None.

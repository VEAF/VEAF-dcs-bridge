# Lot LOT-015 — `dcs-client web` must apply the configured serve host/port/api_key

Status: 🔄 in-progress

**Effort**: S
**Branch**: fix/lot-015

## Problem Statement

`dcs-client.yaml` documents `host`, `port`, and `api_key` as "the dcs-serve address /
the api_key that must match dcs-serve.yaml", but the `web` subcommand never uses them.

`web()` (`src/dcs_bridge/client/app.py`) loads the config yet passes only `cfg.web_port`
to `run_web(web_host, port)`. `run_web` (`client/web/server.py`) opens the browser at
`http://<web_host>:<web_port>` with **no query/hash**. The Leaflet page
(`client/web/static/index.html`) reads the serve target from the URL hash
(`#host=…&port=…&api_key=…`) and, finding none, falls back to `127.0.0.1:8080` with an
**empty api_key**.

Because `dcs-serve` auto-generates an `api_key` (persisted in `dcs-serve.yaml`) and
`/ws/stream` closes the socket with code `4001` on mismatch
(`src/dcs_bridge/serve/api.py`), the web client is stuck on "Disconnected" out of the
box. The only current fix is to hand-craft the URL hash — the documented config file
has no effect on the web client.

Confirmed 2026-07-10 on a local same-machine setup (dcs-serve with a non-empty
api_key): `dcs-client web` connects with empty credentials and is rejected.

## Solution

Make the `web` subcommand propagate the configured serve `host` / `port` / `api_key`
to the browser client so that a filled `dcs-client.yaml` is sufficient — no manual URL
editing.

Two candidate approaches (decide in the ticket):

- **(A) URL hash injection (minimal):** `run_web` receives host/port/api_key and opens
  `http://<web_host>:<web_port>/#host=…&port=…&api_key=…`. Smallest change, reuses the
  existing hash-reading JS. Downsides: key is visible in the address bar; opening the
  port without the hash still fails.
- **(B) Served config endpoint (recommended):** the web server exposes
  `GET /config.json` → `{host, port, api_key}`; the JS fetches it at startup instead of
  parsing the hash. Robust against reloads / manual navigation. Downside: the api_key is
  readable by anyone who can reach `web_port` — acceptable since `web_host` defaults to
  `127.0.0.1` (loopback), but worth a note and keeping the default bind local.

Recommendation: **(B)**, keeping hash values as an optional override if present.

## User Stories

1. As a user who filled `dcs-client.yaml` with my dcs-serve host/port/api_key, I want
   `dcs-client web` to connect the map automatically, so I don't have to hand-edit the
   browser URL with a hash.
2. As a maintainer, I want the documented config fields to actually drive the web
   client, so the template isn't misleading.

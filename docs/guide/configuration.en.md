# Configuration

## dcs-serve.yaml

This file configures the dcs-serve server. It is created automatically on first launch if missing.

```yaml
# TCP address and port on which dcs-serve listens for DCS connections
tcp_host: "0.0.0.0"
tcp_port: 7777

# HTTP/WS address and port for the REST API and WebSocket
http_host: "0.0.0.0"
http_port: 8080

# Bearer token (auto-generated on first launch if empty). Kept as a superuser
# token during the transition to the role-based model (see dcs-tokens.yaml).
api_key: ""

# Path to the role-bearing token store (optional)
tokens_file: "dcs-tokens.yaml"

# Default Lua command timeout, in seconds
default_timeout: 10.0

# Snapshot staleness threshold: if no update is received from DCS
# within this delay, the API returns 503 with {"stale": true}
stale_threshold: 15.0
```

### Key parameters

| Parameter | Default | Description |
|---|---|---|
| `tcp_port` | `7777` | TCP port the Lua script must target |
| `http_port` | `8080` | REST API and WebSocket port |
| `api_key` | *(auto)* | Durable Bearer token; used as a `superuser` token (ADR-0005) |
| `tokens_file` | `dcs-tokens.yaml` | Optional role-bearing token store |
| `default_timeout` | `10.0` | Timeout for `exec` and `spawn` commands |
| `stale_threshold` | `15.0` | Delay before marking the snapshot as stale |

### dcs-tokens.yaml (optional)

Role-bearing tokens replace the single API key (ADR-0005). Each token carries a
role (`observer`/`pilot`/`operator`/`administrator`/`superuser`, or a numeric VEAF
level) and optional `label`/`ucid`/`expiry`:

```yaml
- token: "observer-token"
  role: observer
  label: "read-only dashboard"
- token: "ops-token"
  role: operator
  label: "mission operator"
```

REST clients send their token as `Authorization: Bearer <token>`. If this file is
absent, the `api_key` above keeps working as a `superuser` token.

## dcs-client.yaml

This file configures the clients (TUI, web, MCP).

```yaml
# dcs-serve address
host: "127.0.0.1"
port: 8080

# Bearer token (must match a token accepted by dcs-serve)
api_key: "your-token"

# Local port for the web client's Leaflet map
web_port: 8081
```

The file is looked up in the current directory or via the `--config` option.
`api_key` is the client's durable Bearer token; its role determines which actions
succeed (enforced by dcs-serve).

`dcs-client web` holds this token **server-side** and never exposes it to the
browser (ADR-0005): `GET /config.json` returns only `host`/`port`, and the Leaflet
page opens its WebSocket with a short-lived single-use ticket obtained from the web
server's `POST /ws-ticket` proxy. No credential appears in the page, a URL, or
`/config.json`. `web_port` is the local port the map is served on.

!!! note "No credential in the browser"
    The durable token stays on the web server; the browser only ever receives
    ephemeral WebSocket tickets. The web client binds to `127.0.0.1` by default;
    only pass `--web-host 0.0.0.0` on a trusted network.

## Lua script

The `dcs-bridge.lua` script connects to `dcs-serve` via TCP. Connection parameters are at the top of the file:

```lua
local HOST = "127.0.0.1"   -- dcs-serve address
local PORT = 7777           -- must match tcp_port in dcs-serve.yaml
```

Update these values if DCS World and `dcs-serve` run on different machines.

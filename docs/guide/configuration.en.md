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

# API key (auto-generated on first launch if empty)
api_key: ""

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
| `api_key` | *(auto)* | Key to pass to clients (`X-API-Key`) |
| `default_timeout` | `10.0` | Timeout for `exec` and `spawn` commands |
| `stale_threshold` | `15.0` | Delay before marking the snapshot as stale |

## dcs-client.yaml

This file configures the clients (TUI, web, MCP).

```yaml
# dcs-serve address
host: "127.0.0.1"
port: 8080

# API key (must match dcs-serve.yaml)
api_key: "your-api-key"
```

The file is looked up in the current directory or via the `--config` option.

## Lua script

The `dcs-bridge.lua` script connects to `dcs-serve` via TCP. Connection parameters are at the top of the file:

```lua
local HOST = "127.0.0.1"   -- dcs-serve address
local PORT = 7777           -- must match tcp_port in dcs-serve.yaml
```

Update these values if DCS World and `dcs-serve` run on different machines.

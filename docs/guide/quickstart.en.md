# Quick Start

## 1. Launch dcs-serve

```bash
dcs-serve
```

On first launch, `dcs-serve.yaml` is created with an auto-generated API key. Copy this key into `dcs-client.yaml`.

```
INFO  TCP server listening on 0.0.0.0:9999
INFO  HTTP server listening on 0.0.0.0:8080
INFO  API key: AbCdEfGhIjKlMnOpQrStUvWxYz123456
```

## 2. Inject the Lua script

Copy `dcs-bridge.lua` to your DCS server and inject it into the mission (see [Prerequisites](prerequisites.md)).

Launch DCS World. In the dcs-serve console you should see:

```
INFO  DCS connected from 127.0.0.1
INFO  Snapshot ready — 42 units
```

## 3. Launch a client

=== "Web UI"

    ```bash
    dcs-client web
    ```

    Your browser opens automatically at `http://127.0.0.1:8081` with the Leaflet map.

=== "Terminal TUI"

    ```bash
    dcs-client tui
    ```

    The real-time unit table displays with an integrated Lua REPL.

=== "MCP server (AI agents)"

    Configure your AI agent (Claude, etc.) to use the MCP server:

    ```bash
    dcs-client mcp
    ```

    Available tools: `exec_lua`, `get_units`, `spawn_unit`, `get_mission_info`.

## Network configuration

If `dcs-serve` and clients run on different machines, edit `dcs-client.yaml`:

```yaml
host: "192.168.1.100"   # IP address of the dcs-serve machine
port: 8080
api_key: "your-api-key"
```

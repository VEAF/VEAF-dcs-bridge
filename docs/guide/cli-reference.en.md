# CLI Reference

## dcs-serve

```
Usage: dcs-serve [OPTIONS]

Options:
  --config PATH  Path to dcs-serve.yaml  [default: dcs-serve.yaml]
  --help         Show this message and exit
```

Launches the TCP server (for Lua connection) and the HTTP/WebSocket server (for clients).

## dcs-client

```
Usage: dcs-client COMMAND [OPTIONS]

Commands:
  tui   Textual terminal UI
  web   Local HTTP server with Leaflet map
  mcp   stdio MCP server for AI agents
```

### dcs-client tui

```
Usage: dcs-client tui [OPTIONS]

Options:
  --config PATH  Path to dcs-client.yaml  [default: dcs-client.yaml]
  --help         Show this message and exit
```

Launches the terminal UI with real-time unit table and Lua REPL.

**TUI keyboard shortcuts:**

| Key | Action |
|---|---|
| `Enter` | Execute Lua command |
| `Ctrl+C` | Quit |

### dcs-client web

```
Usage: dcs-client web [OPTIONS]

Options:
  --config PATH  Path to dcs-client.yaml  [default: dcs-client.yaml]
  --port INT     Local HTTP server port    [default: 8081]
  --no-browser   Do not open the browser automatically
  --help         Show this message and exit
```

Launches a local HTTP server and opens the Leaflet map in the browser.

### dcs-client mcp

```
Usage: dcs-client mcp [OPTIONS]

Options:
  --config PATH  Path to dcs-client.yaml  [default: dcs-client.yaml]
  --help         Show this message and exit
```

Launches the MCP server on `stdio`. Use with an MCP-compatible AI agent.

**Exposed MCP tools:**

| Tool | Description |
|---|---|
| `exec_lua(code, timeout?)` | Execute Lua code inside DCS World |
| `get_units()` | Return the list of active units |
| `spawn_unit(group_def)` | Spawn a unit group |
| `get_mission_info()` | Return mission information (theatre…) |

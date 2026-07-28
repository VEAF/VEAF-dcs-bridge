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
  --config PATH      Path to dcs-client.yaml            [default: dcs-client.yaml]
  --web-host TEXT    Bind address for the local HTTP server  [default: 127.0.0.1]
  --web-port INT     Local HTTP server port (0 = use config web_port)  [default: 0]
  --help             Show this message and exit
```

Launches a local HTTP server and opens the Leaflet map in the browser. The web server
reads `host`, `port` and `api_key` from `dcs-client.yaml`; it keeps the token
server-side and serves only `host`/`port` at `GET /config.json`, handing the browser
short-lived WebSocket tickets via `POST /ws-ticket` (no credential in the browser).

### dcs-client mcp

```
Usage: dcs-client mcp [OPTIONS]

Options:
  --config PATH  Path to dcs-client.yaml  [default: dcs-client.yaml]
  --help         Show this message and exit
```

Launches the MCP server on `stdio`. Use with an MCP-compatible AI agent.

**Exposed MCP tools** (a small, fixed set — the client holds no domain knowledge
and proxies the capability-aware catalogue, ADR-0005):

| Tool | Description |
|---|---|
| `list_catalog()` | List the semantic actions available for the running mission |
| `search_catalog(query)` | Search actions and long-tail values (DCS types, VEAF keyphrases) |
| `describe_action(name)` | Describe one action's parameters and valid values |
| `run_action(name, args?, backend?)` | Perform a semantic action (spawn, smoke, remove, run_keyphrase…) |
| `get_units()` | Return the list of active units |
| `capabilities()` | Return the frameworks detected in the mission |
| `exec_lua(code, timeout?)` | Execute raw Lua (requires the `superuser` role) |

**When a tool fails**, it returns a message naming the fix rather than a generic failure —
useful because an MCP agent shows you the string and nothing else:

| Situation | What you get |
|---|---|
| Token unknown, missing or expired (`401`) | Points at `dcs-tokens.yaml` (or the legacy `api_key`) |
| Token valid but role too low (`403`) | Says the **role** is short — a different key will not help |
| Unknown action (`404`) or bad arguments (`400`) | Points at `list_catalog` / `describe_action` |
| DCS not connected or snapshot stale (`503`) | Says DCS is not ready |
| `dcs-serve` not running | `cannot reach dcs-serve at <host>:<port>` — never a raw exception |

dcs-serve's own explanation is included in brackets when it provides one.

!!! note "Timeouts"
    The client waits longer than `dcs-serve` does, so a slow DCS command yields the
    server's verdict instead of a client-side cutoff. `exec_lua(code, timeout=T)` raises
    the client's patience above `T` accordingly.

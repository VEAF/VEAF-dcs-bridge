# dcs-bridge v1.0.0

First public release. **dcs-bridge** connects a running DCS World mission to the
outside world: a small Lua script inside DCS talks to a local server, which exposes the
mission over a REST + WebSocket API — and to a terminal UI, a live map in your browser,
and AI agents.

📖 [Full documentation](https://veaf.github.io/VEAF-dcs-bridge/)

## What's in the download

`dcs-bridge-1.0.0.zip` contains three files:

| File | What it is |
|---|---|
| `dcs-serve.exe` | The bridge server. Talks to DCS, serves the API. No Python needed. |
| `dcs-client.exe` | The clients — terminal UI, browser map, or AI-agent server. |
| `dcs-bridge.lua` | The script to load inside your DCS mission. |

## Getting started

1. Load `dcs-bridge.lua` in your mission (a `DO SCRIPT FILE` trigger at mission start).
2. Run `dcs-serve.exe`. On first start it writes `dcs-serve.yaml` next to itself with a
   freshly generated access token.
3. Run `dcs-client.exe web` for the live map, `dcs-client.exe tui` for the terminal, or
   `dcs-client.exe mcp` to expose the mission to an AI agent.

The server listens on `127.0.0.1:7777` for DCS and `0.0.0.0:8080` for the API.

## Highlights

### Ask for what you want, not how to do it

Rather than making callers write Lua, the bridge exposes an **action catalogue**: named
verbs (`spawn`, `smoke`, `remove`, `run_keyphrase`) with declared parameters. You call
`POST /api/action` with a verb, and the bridge picks how to carry it out.

### It adapts to the mission it finds

At connection time the Lua script announces which frameworks the mission has loaded —
MIST, CTLD, VEAF/VMCT — and the bridge routes each action to the best available one
(VMCT → CTLD → MIST → plain DCS), falling back gracefully when something is absent.
Spawning a FARP uses CTLD's scene manager where CTLD exists and a native DCS static
object where it doesn't, without the caller knowing or caring.

`GET /api/capabilities` reports what was detected, and `GET /api/catalog` lists only the
actions actually available in *this* mission — so a client never offers something that
cannot work.

### Access is graded, not all-or-nothing

Tokens carry a role — `observer`, `pilot`, `operator`, `administrator`, `superuser`,
aligned on the VEAF levels — and every action declares the minimum role it needs.
Watching units is not the same permission as spawning a battalion, and running arbitrary
Lua (`POST /api/exec`) is restricted to `superuser`. Tokens live in `dcs-tokens.yaml`.

Credentials never appear in a URL: the REST API uses `Authorization: Bearer`, and the
WebSocket is opened with a single-use ticket that expires in about ten seconds. The
browser map holds no token at all — the local web server keeps it and fetches tickets on
the page's behalf.

### Three ways in

- **Terminal UI** — live unit table over WebSocket, plus a Lua REPL.
- **Browser map** — Leaflet map with coalition-coloured markers, updating live, and a
  panel of the actions this mission supports. Leaflet ships with the download; no
  internet access required.
- **AI agents (MCP)** — a small, fixed tool set that stays constant no matter how large
  the catalogue grows: agents *discover* actions (`list_catalog`, `search_catalog`,
  `describe_action`) and invoke them through one generic `run_action`.

## Requirements

- Windows for the packaged executables.
- DCS World, with `dcs-bridge.lua` loaded into the mission (VMCT v6 does this for you).
- **One change to your DCS installation**: the script sanitisation in
  `MissionScripting.lua` must be lifted, because the bridge needs `require("socket")` to
  open its connection. Without it nothing connects, whichever way you inject the script.
  It also has to be redone after every DCS update. The
  [Prerequisites](https://veaf.github.io/VEAF-dcs-bridge/guide/prerequisites/) page walks
  through it and explains what you are allowing — if you already run SRS's
  text-to-speech script, it is likely done.
- Nothing else — Python is bundled inside the executables.

## Upgrading from a source checkout

If you have been running dcs-bridge from git before this release, three things changed
in the run-up to 1.0.0 and will break an old client:

- **`X-API-Key` is gone.** Authenticate with `Authorization: Bearer <token>` instead.
  The `api_key` query parameter is gone too — no credential in a URL, so none in a log.
- **The WebSocket takes a ticket, not a key.** `GET /ws/stream?ticket=…`, where the
  ticket comes from `POST /api/ws-ticket`.
- **The MCP tool set changed.** The per-action `spawn_unit` and `get_mission_info` tools
  were retired in favour of catalogue discovery plus a single generic `run_action`.

Your existing `api_key` keeps working as a `superuser` token during the transition, so
the server starts and answers while you migrate.

The default DCS-side TCP port is **7777**. Older documentation said `9999`; if you
copied a config from it, the connection failed silently. That is reconciled everywhere
now, and the Lua script logs its target (`target: <host>:<port>`) when it retries, so a
mismatch is visible in `DCS.log` instead of manifesting as silence.

## Known limitations

- Per-mission custom VEAF aliases are not catalogued — only the VMCT default shortcut
  list is discoverable.
- Framework detection requires an **exact** version match against the version this build
  targets; a locally patched MIST or VEAF script is reported as absent, with the reason
  logged. Looser matching is planned.

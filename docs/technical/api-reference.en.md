# API Reference

REST routes require a **role-bearing token** presented as
`Authorization: Bearer <token>` — no credential ever appears in a URL, query
string, or log. The WebSocket is opened with an **ephemeral single-use ticket**
obtained from `POST /api/ws-ticket` (browsers cannot send custom WS headers).

## Roles (ADR-0005)

Tokens carry a role aligned on VEAF levels; each action declares a minimum role
enforced **by the bridge** before execution:

| VEAF level | Role | Allows |
|---|---|---|
| 0 | `observer` | read-only (units, mission, capabilities, catalogue) |
| 1 | `pilot` | public actions (e.g. `smoke`) |
| 10 | `operator` | the routine catalogue (e.g. `spawn`, `remove`, `run_keyphrase`) |
| 90 | `administrator` | + VEAF admin commands |
| 99 | `superuser` | + raw `POST /api/exec` |

Tokens live server-side in `dcs-tokens.yaml` (`token`, `role`, optional `label`,
`ucid`, `expiry`). The pre-existing single `api_key` keeps working as a
`superuser` token during the transition. In the WEB delegated mode a user's
UCID → role is resolved from `veaf-pilots.txt` **server-side only**, never in the
browser.

## HTTP codes

| Code | Meaning |
|---|---|
| `200` | Success (even if Lua returns an error — the bridge responded) |
| `401` | Missing/invalid/expired token |
| `403` | Token role below the required minimum |
| `503` | DCS not connected or snapshot stale |
| `504` | Command timeout |

---

## REST

### GET /api/units

Returns the list of active units from the snapshot.

**Response 200**

```json
[
  {
    "name": "Enfield 1-1",
    "type": "F-16C_50",
    "coalition": 2,
    "position_dcs": {"x": 123456.0, "y": 5000.0, "z": -45678.0},
    "position_geo": {"lat": 41.123, "lon": 44.567},
    "altitude_agl": 4800.0
  }
]
```

**Response 503** — DCS disconnected or snapshot stale

```json
{"detail": "DCS not connected"}
```

---

### GET /api/mission

Returns information about the current mission.

**Response 200**

```json
{"result": "Caucasus"}
```

---

### POST /api/exec

Executes arbitrary Lua code inside DCS World.

**Request body**

```json
{
  "code": "return coalition.getMainTask(coalition.side.BLUE)",
  "timeout": 5.0
}
```

The `timeout` field is optional (default: `default_timeout` from `dcs-serve.yaml`).

**Response 200**

```json
{"result": "42"}
```

or on Lua error:

```json
{"error": "attempt to index a nil value"}
```

**Response 503** — DCS disconnected

**Response 504** — Timeout

---

### POST /api/spawn

Spawns a unit group in DCS World.

**Request body**

```json
{
  "group_def": {
    "coalition": 2,
    "country": 2,
    "category": "AIRPLANE",
    "name": "Reinforcement",
    "units": [
      {
        "name": "Reinforcement-1",
        "type": "F-16C_50",
        "x": 123456.0,
        "y": -45678.0,
        "alt": 5000.0,
        "heading": 0.0
      }
    ]
  },
  "timeout": 10.0
}
```

**Response 200**

```json
{"result": "42"}
```

The result is the spawned group identifier returned by `coalition.addGroup()`.

---

### POST /api/ws-ticket

Issues an **ephemeral single-use ticket** (default TTL ~10 s) to open the
WebSocket. Requires `Authorization: Bearer <token>` (any role). The ticket is
consumed on first use and expires quickly, so a leaked ticket is already dead.

**Response 200**

```json
{"ticket": "<opaque>", "expires_in": 10.0}
```

---

### POST /api/action

Performs a high-level **semantic action** (ADR-0005). The bridge resolves the verb
in its action registry, selects a backend adapter, generates the Lua and executes
it in DCS. Backend selection follows the global preference order
`VMCT > CTLD > MIST > DCS`, filtered by detected capabilities and by the backends
that can handle the requested `kind` (e.g. a `spawn` vehicle prefers MIST then DCS;
a `farp`/`fob` prefers CTLD then a DCS static). `backend` forces a specific backend
(debug/repro), skipping the capability/kind checks.

**Request body**

```json
{
  "name": "spawn",
  "args": {
    "type": "Hummer",
    "kind": "vehicle",
    "coalition": "blue",
    "position": {"lat": 43.0, "lon": 1.5}
  },
  "backend": null
}
```

- `name`: the verb (`spawn`, `smoke`, `remove`, `run_keyphrase`). Use
  `GET /api/catalog` to discover the available verbs and their parameters.
- `args`: verb parameters. For `spawn`: `type` (DCS type name, required),
  `position` (`{lat, lon}` or `{x, z}`, required), `kind`
  (`vehicle`/`ship`/`plane`/`helicopter`/`farp`/`fob`, default `vehicle`), `coalition`
  (`red`/`blue`/`neutral` or `0`/`1`/`2`, default `blue`), and optional
  `country`, `name`, `heading`, `skill`.
  `country`, `name`, `heading`, `skill`. For `run_keyphrase` (VEAF/VMCT):
  `keyphrase` (marker base such as `-farp`, required), `position` (required),
  optional `params` (mapping appended per VEAF grammar) and `coalition`. The VEAF
  backend composes the keyphrase and calls `veafCommands.execute` without a map
  marker and without a blanket security bypass.
- `backend`: optional, forces a specific backend (debug/repro). Omit to let the
  bridge pick by preference order.

**Response 200**

```json
{"result": "dcs-bridge-Hummer"}
```

The result is the spawned group name.

**Response 400** — unknown/invalid arguments or a forced backend that is unavailable

```json
{"error": "unsupported kind: 'submarine'"}
```

**Response 404** — unknown action name

**Response 503** — DCS disconnected · **Response 504** — timeout

---

### GET /api/capabilities

Returns the frameworks detected in the running mission (ADR-0005). The Lua bridge
announces the loaded frameworks and their versions at the handshake; serve matches
each against the version **this build targets** (lockstep, equality). A framework
loaded at a different version is reported `present: false` with a `reason`, so
routing falls back to a lower backend. The set is cached and cleared on disconnect.

**Response 200**

```json
{
  "connected": true,
  "frameworks": {
    "dcs":  {"present": true,  "version": null,      "targeted": null,      "reason": null},
    "mist": {"present": true,  "version": "4.5.126", "targeted": "4.5.126", "reason": null},
    "ctld": {"present": false, "version": "1.0",     "targeted": "2.0",     "reason": "version mismatch (found 1.0, targeted 2.0)"},
    "veaf": {"present": false, "version": null,      "targeted": "6",       "reason": "not loaded"}
  }
}
```

`frameworks` is empty until the first handshake. DCS is always present.

---

### GET /api/catalog

Returns the **action catalogue** filtered by detected capabilities — the union of
every verb at least one present backend can perform (ADR-0005). Empty until the
first handshake.

**Response 200**

```json
{
  "actions": [
    {
      "name": "spawn",
      "summary": "Spawn a unit or group at a position.",
      "scope": "specific",
      "min_role": "operator",
      "backends": ["dcs"],
      "available_backends": ["dcs"],
      "params": [
        {"name": "type", "type": "string", "required": true, "description": "DCS type name.", "choices": null, "catalog": "dcs_unit_types"},
        {"name": "position", "type": "position", "required": true, "description": "Location as lat/lon or x/z.", "choices": null, "catalog": null}
      ]
    }
  ]
}
```

#### Reference catalogue

Verbs currently implemented in the action registry (`serve/actions.py`). This is
the **theoretical union**: what `GET /api/catalog` actually returns at any moment is
this subset filtered by the present backends (`GET /api/capabilities`). Global
backend preference order: `veaf` > `ctld` > `mist` > `dcs` — the first backend that
is present and able to handle the requested `kind` wins.

| Verb | Summary | Min role | Backends | Scope | Parameters (`*` = required) |
|---|---|---|---|---|---|
| `spawn` | Spawn a unit or group at a position | `operator` | `veaf`, `ctld`, `mist`, `dcs` | portable | `type`* (catalog `dcs_unit_types`), `position`*, `kind` (vehicle/ship/plane/helicopter/farp/fob), `coalition` (red/blue/neutral) |
| `smoke` | Drop a coloured smoke marker at a position | `pilot` | `dcs` | specific | `position`*, `color` (green/red/white/orange/blue) |
| `remove` | Remove (destroy) a group by name | `operator` | `dcs` | specific | `name`* |
| `run_keyphrase` | Run a VEAF/VMCT keyphrase at a position | `operator` | `veaf` | specific | `keyphrase`* (catalog `veaf_shortcuts`), `position`*, `params`, `coalition` (red/blue/neutral) |

For `spawn`, each backend covers only some `kind` values: `mist` the units, `ctld`
and `veaf` the structures (`farp`/`fob`), `dcs` both (a FARP via `dcs` becomes a
static Heliport). A `portable` scope means several backends can perform the verb;
`specific`, that only one can.

#### Effective routing per detected capabilities

The backend actually chosen depends on the present frameworks. The table shows, for
three typical setups, the backend picked by the `veaf` > `ctld` > `mist` > `dcs`
preference and what it produces. DCS is always present; `mist` is absent from all
three cases, so units always go through DCS.

| Capability | **DCS only** | **+ CTLD** | **+ VMCT & CTLD** |
|---|---|---|---|
| `spawn` unit *(vehicle/ship/plane/helicopter)* | `dcs` — `coalition.addGroup` | `dcs` — `coalition.addGroup` | `dcs` — `coalition.addGroup` |
| `spawn` structure *(farp/fob)* | `dcs` — static Heliport | `ctld` — `CTLDSceneManager:playSceneAtPos` scene | `veaf` — keyphrase `-farp`/`-fob` |
| `smoke` | `dcs` | `dcs` | `dcs` |
| `remove` | `dcs` | `dcs` | `dcs` |
| `run_keyphrase` | ✗ not in catalogue | ✗ not in catalogue | `veaf` — `veafCommands.execute` |

- **DCS only** — three verbs; a FARP is a plain static Heliport, no scene logic. No
  `run_keyphrase`.
- **+ CTLD** — same verb list, but a FARP/FOB gains quality via the CTLD scene
  manager instead of a bare static.
- **+ VMCT & CTLD** — `run_keyphrase` appears (VEAF backend); VEAF outranking CTLD, a
  structure goes through the VMCT keyphrase (CTLD stays as fallback).

A `backend=` parameter forces a specific backend (debug/repro), bypassing the
preference — e.g. forcing a FARP as a DCS static even under VMCT.

### GET /api/catalog/search?q=&lt;query&gt;

Searches actions (name/summary/params) and the long-tail value catalogues
(e.g. DCS unit types) for a case-insensitive substring. An empty query matches
nothing.

**Response 200**

```json
{
  "actions": [ /* matching ActionInfo entries */ ],
  "values": [ {"catalog": "dcs_unit_types", "value": "M1A2", "label": "M1A2 Abrams MBT"} ]
}
```

### GET /api/catalog/&lt;name&gt;

Describes one action and resolves its long-tail parameter values, so a client can
discover valid values (e.g. `type`) without loading the whole tail.

**Response 200**

```json
{
  "action": { /* ActionInfo */ },
  "values": {"type": [ {"value": "Hummer", "label": "HMMWV (unarmed)", "tags": ["vehicle", "ground", "usa"]} ]}
}
```

**Response 404** — unknown action

---

## WebSocket

### WS /ws/stream

Real-time event stream.

**Authentication**: `?ticket=<ticket>` query parameter, using a single-use
ticket from `POST /api/ws-ticket`. No durable token appears in the URL.

**On connect**: the full snapshot is sent immediately if DCS is connected.

**Received messages**

#### full_refresh

```json
{
  "type": "full_refresh",
  "units": [ /* array of Unit */ ]
}
```

#### unit_position

```json
{
  "type": "unit_position",
  "data": { /* Unit */ }
}
```

#### unit_spawned

```json
{
  "type": "unit_spawned",
  "data": { /* Unit */ }
}
```

#### unit_destroyed

```json
{
  "type": "unit_destroyed",
  "data": {"name": "Enfield 1-1"}
}
```

---

## Unit model

```json
{
  "name": "string",
  "type": "string",
  "coalition": 0,
  "position_dcs": {
    "x": 0.0,
    "y": 0.0,
    "z": 0.0
  },
  "position_geo": {
    "lat": 0.0,
    "lon": 0.0
  },
  "altitude_agl": 0.0
}
```

**coalition**: `0` = Neutral, `1` = Red, `2` = Blue

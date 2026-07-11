# API Reference

All routes require authentication via the `X-API-Key` header or the `?api_key=<key>` query parameter.

## HTTP codes

| Code | Meaning |
|---|---|
| `200` | Success (even if Lua returns an error — the bridge responded) |
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

- `name`: the verb (currently `spawn`).
- `args`: verb parameters. For `spawn`: `type` (DCS type name, required),
  `position` (`{lat, lon}` or `{x, z}`, required), `kind`
  (`vehicle`/`ship`/`plane`/`helicopter`/`farp`/`fob`, default `vehicle`), `coalition`
  (`red`/`blue`/`neutral` or `0`/`1`/`2`, default `blue`), and optional
  `country`, `name`, `heading`, `skill`.
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

**Authentication**: `?api_key=<key>` query parameter.

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

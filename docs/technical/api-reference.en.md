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
it in DCS. The tracer-bullet slice (LOT-018) ships the `spawn` verb with a single
DCS-native backend — no MIST dependency.

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
  (`vehicle`/`ship`/`plane`/`helicopter`, default `vehicle`), `coalition`
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

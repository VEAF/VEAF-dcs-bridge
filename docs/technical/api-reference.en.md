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

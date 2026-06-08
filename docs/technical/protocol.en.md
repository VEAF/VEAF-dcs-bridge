# Wire Protocol

## Transport

The protocol uses **newline-delimited JSON** over TCP. Each message is a JSON line terminated by `\n`.

- **Connection**: the Lua script connects to `dcs-serve` (outgoing connection from DCS)
- **Upward direction** (DCS → serve): `full_refresh` and spontaneous events
- **Downward direction** (serve → DCS): commands to execute

## Upward messages (DCS → dcs-serve)

### full_refresh

Sent every 5 seconds. Atomically replaces the full snapshot.

```json
{
  "type": "full_refresh",
  "units": [
    {
      "name": "Enfield 1-1",
      "type": "F-16C_50",
      "coalition": 2,
      "position_dcs": {"x": 123456.0, "y": 5000.0, "z": -45678.0},
      "position_geo": {"lat": 41.123, "lon": 44.567},
      "altitude_agl": 4800.0
    }
  ]
}
```

### unit_position

Emitted on each significant position change.

```json
{
  "type": "unit_position",
  "data": {
    "name": "Enfield 1-1",
    "type": "F-16C_50",
    "coalition": 2,
    "position_dcs": {"x": 123456.0, "y": 5000.0, "z": -45678.0},
    "position_geo": {"lat": 41.123, "lon": 44.567},
    "altitude_agl": 4800.0
  }
}
```

### unit_spawned

Emitted when a new unit appears.

```json
{
  "type": "unit_spawned",
  "data": { /* same structure as unit_position */ }
}
```

### unit_destroyed

Emitted when a unit is destroyed.

```json
{
  "type": "unit_destroyed",
  "data": {"name": "Enfield 1-1"}
}
```

### Response (reply to a command)

```json
{
  "id": "command-uuid",
  "result": "value returned by Lua",
  "error": null
}
```

Exactly one of `result` or `error` is non-null.

## Downward messages (dcs-serve → DCS)

### Command exec

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "action": "exec",
  "payload": {"code": "return coalition.getMainTask(coalition.side.BLUE)"}
}
```

### Command spawn

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "action": "spawn",
  "payload": {
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
    }
  }
}
```

## Enum values

### Coalition

| Value | Meaning |
|---|---|
| `0` | Neutral |
| `1` | Red |
| `2` | Blue |

### CommandAction

| Value | Description |
|---|---|
| `"exec"` | Execute arbitrary Lua code |
| `"spawn"` | Spawn a group via `coalition.addGroup()` |

### EventName

| Value | Description |
|---|---|
| `"unit_position"` | Unit position update |
| `"unit_spawned"` | New unit appeared |
| `"unit_destroyed"` | Unit was destroyed |

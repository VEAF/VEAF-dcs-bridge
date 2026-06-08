# Protocole fil de fer

## Transport

Le protocole utilise **JSON newline-delimited** sur TCP. Chaque message est une ligne JSON terminée par `\n`.

- **Connexion** : le script Lua se connecte à `dcs-serve` (connexion sortante depuis DCS)
- **Direction montante** (DCS → serve) : `full_refresh` et événements spontanés
- **Direction descendante** (serve → DCS) : commandes à exécuter

## Messages montants (DCS → dcs-serve)

### full_refresh

Envoyé toutes les 5 secondes. Remplace atomiquement le snapshot complet.

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

Émis à chaque changement de position significatif.

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

Émis à l'apparition d'une nouvelle unité.

```json
{
  "type": "unit_spawned",
  "data": { /* même structure que unit_position */ }
}
```

### unit_destroyed

Émis à la destruction d'une unité.

```json
{
  "type": "unit_destroyed",
  "data": {"name": "Enfield 1-1"}
}
```

### Response (réponse à une commande)

```json
{
  "id": "uuid-de-la-commande",
  "result": "valeur retournée par le Lua",
  "error": null
}
```

Exactement un des champs `result` ou `error` est non-null.

## Messages descendants (dcs-serve → DCS)

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

## Valeurs des enums

### Coalition

| Valeur | Signification |
|---|---|
| `0` | Neutral |
| `1` | Red |
| `2` | Blue |

### CommandAction

| Valeur | Description |
|---|---|
| `"exec"` | Exécuter du code Lua arbitraire |
| `"spawn"` | Faire apparaître un groupe via `coalition.addGroup()` |

### EventName

| Valeur | Description |
|---|---|
| `"unit_position"` | Mise à jour de position d'une unité |
| `"unit_spawned"` | Apparition d'une nouvelle unité |
| `"unit_destroyed"` | Destruction d'une unité |

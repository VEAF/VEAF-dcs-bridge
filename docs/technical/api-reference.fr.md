# Référence API

Toutes les routes nécessitent l'authentification via l'en-tête `X-API-Key` ou le paramètre de requête `?api_key=<clé>`.

## Codes HTTP

| Code | Signification |
|---|---|
| `200` | Succès (même si Lua retourne une erreur — le bridge a répondu) |
| `503` | DCS non connecté ou snapshot périmé |
| `504` | Timeout de la commande |

---

## REST

### GET /api/units

Retourne la liste des unités actives depuis le snapshot.

**Réponse 200**

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

**Réponse 503** — DCS déconnecté ou snapshot périmé

```json
{"detail": "DCS not connected"}
```

---

### GET /api/mission

Retourne les informations de la mission en cours.

**Réponse 200**

```json
{"result": "Caucasus"}
```

---

### POST /api/exec

Exécute du code Lua arbitraire dans DCS World.

**Corps de la requête**

```json
{
  "code": "return coalition.getMainTask(coalition.side.BLUE)",
  "timeout": 5.0
}
```

Le champ `timeout` est optionnel (défaut : `default_timeout` de `dcs-serve.yaml`).

**Réponse 200**

```json
{"result": "42"}
```

ou en cas d'erreur Lua :

```json
{"error": "attempt to index a nil value"}
```

**Réponse 503** — DCS déconnecté

**Réponse 504** — Timeout

---

### POST /api/spawn

Fait apparaître un groupe d'unités dans DCS World.

**Corps de la requête**

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

**Réponse 200**

```json
{"result": "42"}
```

Le résultat est l'identifiant du groupe spawné retourné par `coalition.addGroup()`.

---

## WebSocket

### WS /ws/stream

Flux d'événements en temps réel.

**Authentification** : paramètre de requête `?api_key=<clé>`.

**Connexion** : à la connexion, le snapshot complet est envoyé immédiatement si le DCS est connecté.

**Messages reçus**

#### full_refresh

```json
{
  "type": "full_refresh",
  "units": [ /* tableau d'Unit */ ]
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

## Modèle Unit

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

**coalition** : `0` = Neutral, `1` = Red, `2` = Blue

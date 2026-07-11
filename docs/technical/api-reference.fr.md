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

### POST /api/action

Exécute une **action sémantique** de haut niveau (ADR-0005). Le bridge résout le
verbe dans son registre d'actions, sélectionne un adaptateur de backend, génère le
Lua et l'exécute dans DCS. La tranche « tracer-bullet » (LOT-018) livre le verbe
`spawn` avec un unique backend DCS natif — sans dépendance à MIST.

**Corps de la requête**

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

- `name` : le verbe (actuellement `spawn`).
- `args` : paramètres du verbe. Pour `spawn` : `type` (nom de type DCS, requis),
  `position` (`{lat, lon}` ou `{x, z}`, requis), `kind`
  (`vehicle`/`ship`/`plane`/`helicopter`, défaut `vehicle`), `coalition`
  (`red`/`blue`/`neutral` ou `0`/`1`/`2`, défaut `blue`), et en option
  `country`, `name`, `heading`, `skill`.
- `backend` : optionnel, force un backend précis (debug/repro). À omettre pour
  laisser le bridge choisir selon l'ordre de préférence.

**Réponse 200**

```json
{"result": "dcs-bridge-Hummer"}
```

Le résultat est le nom du groupe spawné.

**Réponse 400** — arguments inconnus/invalides ou backend forcé indisponible

```json
{"error": "unsupported kind: 'submarine'"}
```

**Réponse 404** — nom d'action inconnu

**Réponse 503** — DCS déconnecté · **Réponse 504** — timeout

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

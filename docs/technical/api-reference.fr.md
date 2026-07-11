# Référence API

Les routes REST nécessitent un **token porteur de rôle**, présenté via
`Authorization: Bearer <token>` — aucun credential n'apparaît jamais dans une URL,
une query string ou un log. Le WebSocket s'ouvre avec un **ticket éphémère à usage
unique** obtenu via `POST /api/ws-ticket` (les navigateurs ne peuvent pas envoyer
d'en-têtes WS personnalisés).

## Rôles (ADR-0005)

Les tokens portent un rôle aligné sur les niveaux VEAF ; chaque action déclare un
rôle minimum, appliqué **par le bridge** avant l'exécution :

| Niveau VEAF | Rôle | Autorise |
|---|---|---|
| 0 | `observer` | lecture seule (unités, mission, capacités, catalogue) |
| 1 | `pilot` | actions publiques (p. ex. `smoke`) |
| 10 | `operator` | le catalogue courant (p. ex. `spawn`, `remove`, `run_keyphrase`) |
| 90 | `administrator` | + commandes admin VEAF |
| 99 | `superuser` | + `POST /api/exec` (code brut) |

Les tokens vivent côté serveur dans `dcs-tokens.yaml` (`token`, `role`, et en
option `label`, `ucid`, `expiry`). La clé `api_key` unique préexistante continue de
fonctionner comme un token `superuser` pendant la transition. En mode délégué WEB,
le rôle d'un utilisateur est résolu depuis son UCID via `veaf-pilots.txt`
**uniquement côté serveur**, jamais dans le navigateur.

## Codes HTTP

| Code | Signification |
|---|---|
| `200` | Succès (même si Lua retourne une erreur — le bridge a répondu) |
| `401` | Token manquant/invalide/expiré |
| `403` | Rôle du token inférieur au minimum requis |
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

### POST /api/ws-ticket

Émet un **ticket éphémère à usage unique** (TTL ~10 s par défaut) pour ouvrir le
WebSocket. Nécessite `Authorization: Bearer <token>` (n'importe quel rôle). Le
ticket est consommé à la première utilisation et expire vite : un ticket fuité est
déjà mort.

**Réponse 200**

```json
{"ticket": "<opaque>", "expires_in": 10.0}
```

---

### POST /api/action

Exécute une **action sémantique** de haut niveau (ADR-0005). Le bridge résout le
verbe dans son registre d'actions, sélectionne un adaptateur de backend, génère le
Lua et l'exécute dans DCS. La sélection du backend suit l'ordre de préférence global
`VMCT > CTLD > MIST > DCS`, filtré par les capacités détectées et par les backends
capables de traiter le `kind` demandé (p. ex. un `spawn` de véhicule préfère MIST
puis DCS ; un `farp`/`fob` préfère CTLD puis un objet statique DCS). `backend` force un
backend précis (debug/repro), en contournant les contrôles de capacité/kind.

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

- `name` : le verbe (`spawn`, `smoke`, `remove`, `run_keyphrase`). Utilisez
  `GET /api/catalog` pour découvrir les verbes disponibles et leurs paramètres.
- `args` : paramètres du verbe. Pour `spawn` : `type` (nom de type DCS, requis),
  `position` (`{lat, lon}` ou `{x, z}`, requis), `kind`
  (`vehicle`/`ship`/`plane`/`helicopter`/`farp`/`fob`, défaut `vehicle`), `coalition`
  (`red`/`blue`/`neutral` ou `0`/`1`/`2`, défaut `blue`), et en option
  `country`, `name`, `heading`, `skill`.
  `country`, `name`, `heading`, `skill`. Pour `run_keyphrase` (VEAF/VMCT) :
  `keyphrase` (base du marqueur, p. ex. `-farp`, requis), `position` (requis),
  et en option `params` (dictionnaire ajouté selon la grammaire VEAF) et
  `coalition`. Le backend VEAF compose la keyphrase et appelle
  `veafCommands.execute` sans marqueur sur la carte et sans bypass de sécurité
  global.
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

### GET /api/capabilities

Renvoie les frameworks détectés dans la mission en cours (ADR-0005). Le bridge Lua
annonce les frameworks chargés et leurs versions au handshake ; le service `serve`
compare chacune à la version que **ce build cible** (lockstep, égalité stricte). Un
framework chargé dans une version différente est signalé `present: false` avec un
`reason`, et le routage retombe sur un backend inférieur. Le jeu est mis en cache
et vidé à la déconnexion.

**Réponse 200**

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

`frameworks` est vide tant qu'aucun handshake n'a eu lieu. DCS est toujours présent.

---

### GET /api/catalog

Renvoie le **catalogue d'actions** filtré par les capacités détectées — l'union de
tous les verbes qu'au moins un backend présent peut exécuter (ADR-0005). Vide tant
qu'aucun handshake n'a eu lieu.

**Réponse 200**

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

#### Catalogue de référence

Verbes actuellement implémentés dans le registre d'actions (`serve/actions.py`).
C'est l'**union théorique** : ce que renvoie réellement `GET /api/catalog` à un
instant T est ce sous-ensemble filtré par les backends présents
(`GET /api/capabilities`). Ordre de préférence backend global : `veaf` > `ctld` >
`mist` > `dcs` — le premier backend présent et capable du `kind` demandé est retenu.

| Verbe | Résumé | Rôle min | Backends | Portée | Paramètres (`*` = requis) |
|---|---|---|---|---|---|
| `spawn` | Fait apparaître une unité/un groupe à une position | `operator` | `veaf`, `ctld`, `mist`, `dcs` | portable | `type`* (catalogue `dcs_unit_types`), `position`*, `kind` (vehicle/ship/plane/helicopter/farp/fob), `coalition` (red/blue/neutral) |
| `smoke` | Lâche un fumigène coloré à une position | `pilot` | `dcs` | spécifique | `position`*, `color` (green/red/white/orange/blue) |
| `remove` | Détruit un groupe par son nom | `operator` | `dcs` | spécifique | `name`* |
| `run_keyphrase` | Exécute une keyphrase VEAF/VMCT à une position | `operator` | `veaf` | spécifique | `keyphrase`* (catalogue `veaf_shortcuts`), `position`*, `params`, `coalition` (red/blue/neutral) |

Pour `spawn`, chaque backend ne couvre qu'une partie des `kind` : `mist` les unités,
`ctld` et `veaf` les structures (`farp`/`fob`), `dcs` les deux (une FARP via `dcs`
devient un static Heliport). Une portée `portable` signifie que plusieurs backends
savent exécuter le verbe ; `spécifique`, qu'un seul le sait.

#### Routage effectif par capacités détectées

Le backend réellement retenu dépend des frameworks présents. Le tableau montre, pour
trois configurations types, le backend choisi par la préférence `veaf` > `ctld` >
`mist` > `dcs` et ce qu'il produit. DCS est toujours présent ; `mist` est absent des
trois cas, donc les unités passent toujours par DCS.

| Capacité | **DCS pur** | **+ CTLD** | **+ VMCT & CTLD** |
|---|---|---|---|
| `spawn` unité *(vehicle/ship/plane/helicopter)* | `dcs` — `coalition.addGroup` | `dcs` — `coalition.addGroup` | `dcs` — `coalition.addGroup` |
| `spawn` structure *(farp/fob)* | `dcs` — static Heliport | `ctld` — scène `CTLDSceneManager:playSceneAtPos` | `veaf` — keyphrase `-farp`/`-fob` |
| `smoke` | `dcs` | `dcs` | `dcs` |
| `remove` | `dcs` | `dcs` | `dcs` |
| `run_keyphrase` | ✗ absent du catalogue | ✗ absent du catalogue | `veaf` — `veafCommands.execute` |

- **DCS pur** — trois verbes ; une FARP est un simple static Heliport, sans logique
  de scène. Pas de `run_keyphrase`.
- **+ CTLD** — même liste de verbes, mais une FARP/FOB monte en qualité via le
  gestionnaire de scènes CTLD au lieu d'un static nu.
- **+ VMCT & CTLD** — `run_keyphrase` apparaît (backend VEAF) ; VEAF étant prioritaire
  sur CTLD, une structure part via la keyphrase VMCT (CTLD reste en repli).

Un paramètre `backend=` force un backend précis (debug/repro) et court-circuite la
préférence — p. ex. forcer une FARP en static DCS même sous VMCT.

### GET /api/catalog/search?q=&lt;requête&gt;

Recherche dans les actions (nom/résumé/paramètres) et dans les catalogues de
valeurs de la longue traîne (p. ex. les types d'unités DCS) une sous-chaîne
insensible à la casse. Une requête vide ne renvoie rien.

**Réponse 200**

```json
{
  "actions": [ /* entrées ActionInfo correspondantes */ ],
  "values": [ {"catalog": "dcs_unit_types", "value": "M1A2", "label": "M1A2 Abrams MBT"} ]
}
```

### GET /api/catalog/&lt;nom&gt;

Décrit une action et résout les valeurs de longue traîne de ses paramètres, pour
qu'un client puisse découvrir les valeurs valides (p. ex. `type`) sans charger
toute la traîne.

**Réponse 200**

```json
{
  "action": { /* ActionInfo */ },
  "values": {"type": [ {"value": "Hummer", "label": "HMMWV (unarmed)", "tags": ["vehicle", "ground", "usa"]} ]}
}
```

**Réponse 404** — action inconnue

---

## WebSocket

### WS /ws/stream

Flux d'événements en temps réel.

**Authentification** : paramètre de requête `?ticket=<ticket>`, avec un ticket à
usage unique obtenu via `POST /api/ws-ticket`. Aucun token durable n'apparaît dans
l'URL.

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

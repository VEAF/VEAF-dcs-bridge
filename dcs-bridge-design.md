# dcs-bridge — Design Document

> Statut : design validé / implémentation non démarrée  
> Date : 2026-06-07

---

## Contexte

Witchcraft (jboecker/dcs-witchcraft) est un outil de débogage Lua pour DCS World : il ouvre une connexion TCP depuis la mission vers un serveur Node.js, et expose une interface web pour exécuter du code Lua en live.

`dcs-bridge` s'inspire de cette approche pour en faire un outil plus générique, plus moderne, et exposé via plusieurs interfaces. Cas d'usage initial : piloter DCS depuis un agent IA (Claude) pour exécuter des tests d'intégration automatisés.

---

## Positionnement

| Critère | Décision |
|---|---|
| Repo | Indépendant : `github.com/VEAF/dcs-bridge` |
| Langage | Python (Poetry) |
| Relation avec `veaf-tools` | Aucune dépendance de code — projets découplés |
| Réutilisabilité | Générique, utilisable hors contexte VEAF |

---

## Architecture

```
DCS World (Lua socket)
    └──── TCP socket ────► dcs-serve  (FastAPI + asyncio)
                                ├── REST   /api/*       commandes ponctuelles
                                └── WS     /ws/stream   positions en temps réel

Consommateurs :
    dcs-client --tui    →  REST + WebSocket  (Textual)
    dcs-client --web    →  REST + WebSocket  (HTML/JS statique + Leaflet)
    dcs-client --mcp    →  REST              (MCP server)
    Site web VEAF       →  REST + WebSocket  (client Python externe)
```

---

## Composants

### 1. Lua bridge (côté DCS)

- Script Lua injecté dans la mission via `dofile` (MissionScripting.lua) **ou** trigger DCS (`DO SCRIPT FILE`) — les deux méthodes sont supportées
- Ouvre une connexion TCP sortante vers `dcs-serve`
- Protocole : JSON newline-delimited (`\n`)
- Reconnexion : retry infini avec backoff exponentiel, warning dans le log DCS après N secondes sans connexion (voir ADR-0003)
- Socket non-bloquante (`settimeout(0.0001)`) — la mission ne gèle jamais
- Schedulé via `timer.scheduleFunction` toutes les 100ms (même approche que Witchcraft)
- Envoie un **Full Refresh** toutes les 5 secondes (état complet de toutes les unités)
- Calcule lui-même `position_geo` (lat/lon) via `coord.LOtoLL()` et `altitude_agl` via `land.getHeight()` (voir ADR-0001)

### 2. `dcs-serve`

- Processus Python long-running, tourne sur la machine du serveur DCS
- Gère la connexion TCP entrante depuis DCS
- Maintient un **Snapshot** en mémoire (voir ADR-0002)
- Expose une API FastAPI :
  - `POST /api/exec` — exécuter du Lua arbitraire
  - `POST /api/spawn` — spawner une unité
  - `GET  /api/units` — snapshot des unités (servi depuis le cache)
  - `GET  /api/mission` — informations sur la mission courante
  - `WS   /ws/stream` — flux temps réel (events delta + full refresh toutes les 5s)
- Authentification : API Key obligatoire (`X-API-Key`), générée au premier démarrage
- Config : `dcs-serve.yaml`

#### Gestion des erreurs HTTP

| Situation | Code HTTP |
|---|---|
| Lua exécuté, erreur runtime | 200 `{ "success": false, "error": "..." }` |
| Timeout (DCS ne répond pas) | 504 Gateway Timeout |
| DCS déconnecté | 503 Service Unavailable |
| Snapshot pas encore reçu | 503 `{ "ready": false }` |
| Snapshot stale | 200 `{ "stale": true, "last_updated": "..." }` |

#### Timeout `/api/exec`

- Timeout global configurable dans `dcs-serve.yaml` (défaut 30s)
- Overridable par requête via `{ "code": "...", "timeout": 120 }`, plafonné par le global

### 3. `dcs-client`

Sous-commande Python avec plusieurs modes :

| Flag | Interface | Technologie |
|---|---|---|
| `--tui` | Terminal UI interactive | Textual |
| `--web` | WebUI avec carte | HTML/JS statique (Leaflet) servi localement, navigateur ouvert automatiquement |
| `--mcp` | MCP server pour agents IA | SDK `mcp` (Anthropic) |

Config : `dcs-client.yaml`

#### Outils MCP (v1)

- `exec_lua(code, timeout?)` — exécuter du Lua arbitraire
- `get_units()` — snapshot des unités
- `spawn_unit(group_def)` — spawner une unité
- `get_mission_info()` — informations sur la mission

---

## Protocole TCP (DCS ↔ dcs-serve)

Format : JSON newline-delimited (`\n` comme délimiteur de message).

```json
// serve → DCS : commande à exécuter (Command)
{ "id": "abc123", "action": "exec", "payload": { "code": "..." } }

// DCS → serve : réponse à une commande (Response)
{ "id": "abc123", "result": "...", "error": null }

// DCS → serve : événement spontané (Event)
{ "type": "event", "name": "unit_position", "data": { ... } }

// DCS → serve : full refresh (toutes les 5s)
{ "type": "full_refresh", "units": [ ... ] }
```

---

## Modèle de données `unit`

```json
{
  "name": "unit_name",
  "position_dcs": { "x": 0, "y": 0, "z": 0 },
  "position_geo": { "lat": 41.123, "lon": 41.456 },
  "altitude_agl": 42.3,
  "category": "vehicle",
  "type": "T-80",
  "coalition": 1
}
```

---

## Structure du projet Python

```
src/
  dcs_bridge/
    serve/        # FastAPI + handler TCP asyncio + snapshot
    client/
      tui/        # Textual
      web/        # serveur HTTP statique + fichiers Leaflet
        static/
      mcp/        # MCP server
    common/       # types Pydantic partagés, protocole
```

Un seul package `dcs_bridge` dans `pyproject.toml` (Poetry).

---

## Configuration

### `dcs-serve.yaml`

```yaml
serve:
  host: "0.0.0.0"
  port: 8080
  api_key: "<auto-generated>"
  exec_timeout_default: 30
  exec_timeout_max: 300

dcs:
  tcp_host: "0.0.0.0"
  tcp_port: 9001
  snapshot_interval: 5        # Full Refresh toutes les N secondes
  reconnect_backoff_max: 60   # Backoff max en secondes
  reconnect_warn_after: 30    # Warning après N secondes sans connexion
```

### `dcs-client.yaml`

```yaml
serve:
  host: "localhost"
  port: 8080
  api_key: "<à renseigner>"
```

---

## Toolchain

| Outil | Rôle |
|---|---|
| Poetry | Gestion des dépendances et packaging |
| Ruff | Lint + format |
| Mypy | Typage statique |
| Pytest (style fonctionnel) | Tests unitaires + intégration |
| PyInstaller | Binaires Windows (groupe `build`) |
| GitHub Actions | CI + release binaires |

---

## Stratégie de test

- **Unitaires** : logique pure — parsing, buffer TCP, corrélation id/timeout, snapshot stale/ready
- **Intégration** : `httpx.AsyncClient` (FastAPI) + faux serveur DCS TCP en fixture pytest
- **E2E** : manuel uniquement (vrai DCS)

---

## Distribution

- `pip install dcs-bridge` (PyPI) — pour les développeurs
- Binaires Windows compilés (PyInstaller + GitHub Actions) — pour les utilisateurs DCS non-techniques

---

## Ordre d'implémentation

1. Setup projet (Poetry, pyproject.toml, structure `src/`)
2. Types partagés (`common/`) — modèles Pydantic, schémas protocole
3. Script Lua bridge — connexion TCP, backoff, full refresh, conversion coords
4. `dcs-serve` core — handler TCP asyncio, snapshot, corrélation id/timeout (TDD)
5. `dcs-serve` API — endpoints FastAPI, WS stream, API key auth (TDD)
6. `dcs-client --tui` — Textual
7. `dcs-client --mcp` — MCP server
8. `dcs-client --web` — serveur HTTP + Leaflet
9. Packaging — PyInstaller + CI GitHub Actions

---

## Ce que ce projet n'est PAS

- Pas un remplacement de DCS-gRPC (pas de streaming binaire, pas de Protobuf)
- Pas un frontend React/Vue (WebUI = HTML statique simple)
- Pas intégré dans `veaf-tools` (outils et cycles de vie distincts)

---

## ADRs

- [ADR-0001](docs/adr/0001-lua-coord-conversion.md) — Conversion de coordonnées effectuée côté Lua
- [ADR-0002](docs/adr/0002-push-based-snapshot.md) — Cache snapshot push-based dans dcs-serve
- [ADR-0003](docs/adr/0003-reconnexion-lua-backoff.md) — Reconnexion TCP Lua bridge — retry infini avec backoff exponentiel

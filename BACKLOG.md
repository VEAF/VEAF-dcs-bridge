# dcs-bridge — Backlog

## Summary

| ID | Description | Effort | Status |
|---|---|---|---|
| LOT-001 | Setup projet Poetry + structure src/ | S | ✅ |
| LOT-002 | Types partagés common/ | S | ✅ |
| LOT-003 | Script Lua bridge | M | ⬜ |
| LOT-004 | dcs-serve core (TCP asyncio + snapshot) | L | ⬜ |
| LOT-005 | dcs-serve API (FastAPI + WS + auth) | L | ⬜ |
| LOT-006 | dcs-client --tui (Textual) | M | ⬜ |
| LOT-007 | dcs-client --mcp (MCP server) | M | ⬜ |
| LOT-008 | dcs-client --web (HTTP statique + Leaflet) | M | ⬜ |
| LOT-009 | Packaging PyInstaller + CI GitHub Actions | M | ⬜ |

---

## LOT-001 — Setup projet Poetry + structure src/

**Status:** ✅  
**Effort:** S

**Tickets:**
- [x] Initialiser `pyproject.toml` avec Poetry (dépendances: fastapi, uvicorn, textual, mcp, pydantic, pyyaml)
- [x] Créer la structure `src/dcs_bridge/serve/`, `client/tui/`, `client/web/static/`, `client/mcp/`, `common/`
- [x] Créer la structure `test/`
- [x] Configurer ruff, mypy, pytest dans `pyproject.toml`
- [x] Ajouter `.editorconfig`

---

## LOT-002 — Types partagés common/

**Status:** ⬜  
**Effort:** S

**Tickets:**
- [ ] Modèles Pydantic : `Unit`, `UnitPosition`, `Command`, `Response`, `Event`, `FullRefresh`
- [ ] Schémas protocole TCP (JSON newline-delimited)
- [ ] Tests unitaires des modèles

---

## LOT-003 — Script Lua bridge

**Status:** ⬜  
**Effort:** M

**Tickets:**
- [ ] Connexion TCP sortante vers dcs-serve
- [ ] Reconnexion avec backoff exponentiel + warning log après N secondes (ADR-0003)
- [ ] Socket non-bloquante (`settimeout(0.0001)`)
- [ ] Full Refresh toutes les 5 secondes (toutes les unités)
- [ ] Envoi des events spontanés (positions, destructions)
- [ ] Conversion coordonnées via `coord.LOtoLL()` + `land.getHeight()` (ADR-0001)
- [ ] Exécution des Commands reçues (`exec`, `spawn`)
- [ ] Support injection via MissionScripting.lua ET trigger DO SCRIPT FILE

---

## LOT-004 — dcs-serve core

**Status:** ⬜  
**Effort:** L

**Tickets:**
- [ ] Handler TCP asyncio (écoute, accepte la connexion DCS)
- [ ] Parser JSON newline-delimited
- [ ] Maintien du Snapshot en mémoire (ADR-0002)
- [ ] Mise à jour Snapshot via Events + Full Refresh
- [ ] Gestion état `ready` / `stale` avec timestamp
- [ ] Corrélation Command/Response par `id` avec timeout configurable
- [ ] Gestion déconnexion DCS (503 / stale)
- [ ] Tests d'intégration avec faux serveur DCS TCP (fixture pytest)

---

## LOT-005 — dcs-serve API

**Status:** ⬜  
**Effort:** L

**Tickets:**
- [ ] `POST /api/exec` avec timeout global + override par requête
- [ ] `POST /api/spawn`
- [ ] `GET /api/units` (depuis Snapshot)
- [ ] `GET /api/mission`
- [ ] `WS /ws/stream` (events delta + full refresh toutes les 5s)
- [ ] Middleware API Key (`X-API-Key`)
- [ ] Génération automatique de la clé au premier démarrage
- [ ] Config `dcs-serve.yaml` (chargement + valeurs par défaut)
- [ ] Codes HTTP corrects (200/503/504 selon ADR)
- [ ] Tests FastAPI avec `httpx.AsyncClient`

---

## LOT-006 — dcs-client --tui

**Status:** ⬜  
**Effort:** M

**Tickets:**
- [ ] Affichage snapshot des unités (tableau)
- [ ] Input Lua arbitraire + affichage résultat
- [ ] Connexion WS pour mise à jour temps réel
- [ ] Config `dcs-client.yaml`

---

## LOT-007 — dcs-client --mcp

**Status:** ⬜  
**Effort:** M

**Tickets:**
- [ ] Outil `exec_lua(code, timeout?)`
- [ ] Outil `get_units()`
- [ ] Outil `spawn_unit(group_def)`
- [ ] Outil `get_mission_info()`
- [ ] Tests unitaires des outils MCP

---

## LOT-008 — dcs-client --web

**Status:** ⬜  
**Effort:** M

**Tickets:**
- [ ] Serveur HTTP statique local (FastAPI StaticFiles)
- [ ] Ouverture automatique du navigateur
- [ ] Page Leaflet avec unités colorées par coalition
- [ ] Tooltip au survol (nom, type, altitude)
- [ ] Connexion WebSocket pour mise à jour temps réel

---

## LOT-009 — Packaging

**Status:** ⬜  
**Effort:** M

**Tickets:**
- [ ] `dcs-serve.spec` PyInstaller
- [ ] `dcs-client.spec` PyInstaller
- [ ] Workflow GitHub Actions `release.yml` (build + publish)
- [ ] Publication PyPI

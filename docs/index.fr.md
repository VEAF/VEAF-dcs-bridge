# dcs-bridge

**dcs-bridge** est un pont générique entre DCS World et des consommateurs externes (TUI, interface web, agents IA).

## Vue d'ensemble

```mermaid
graph LR
    DCS["DCS World\n(Lua bridge)"]
    SERVE["dcs-serve\n(TCP → HTTP/WS)"]
    TUI["dcs-client tui\n(Textual TUI)"]
    WEB["dcs-client web\n(Leaflet map)"]
    MCP["dcs-client mcp\n(MCP tools)"]
    AI["Agent IA\n(Claude, GPT…)"]

    DCS -->|TCP JSON| SERVE
    SERVE -->|HTTP REST| TUI
    SERVE -->|WebSocket| TUI
    SERVE -->|HTTP REST| WEB
    SERVE -->|WebSocket| WEB
    SERVE -->|HTTP REST| MCP
    MCP -->|stdio MCP| AI
```

## Fonctionnalités

- **Bridge Lua** — injecté dans DCS World, envoie les positions des unités et les événements en temps réel
- **dcs-serve** — serveur TCP/HTTP/WebSocket, snapshot en mémoire, actions capability-aware, authentification par rôle (token Bearer)
- **dcs-client tui** — interface terminal Textual avec tableau des unités en temps réel et REPL Lua
- **dcs-client web** — carte Leaflet avec marqueurs colorés par coalition, mise à jour en temps réel
- **dcs-client mcp** — serveur MCP exposant `exec_lua`, `get_units`, `spawn_unit`, `get_mission_info`

## Démarrage rapide

```bash
# 1. Lancer le serveur
dcs-serve

# 2. Ouvrir l'interface web (dans un autre terminal)
dcs-client web

# 3. Ou lancer le TUI
dcs-client tui
```

Consultez le [Guide d'installation](guide/installation.md) pour les instructions complètes.

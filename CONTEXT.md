---
name: dcs-bridge-context
description: Glossaire du domaine dcs-bridge — termes canoniques du projet
metadata:
  type: reference
---

# Glossaire — dcs-bridge

## Composants

**dcs-bridge**
Nom du projet. Pont générique entre DCS World et des consommateurs externes (TUI, WebUI, agents IA). Indépendant du contexte VEAF.

**dcs-serve**
Processus Python long-running qui tourne sur la machine hébergeant DCS. Reçoit la connexion TCP depuis DCS, maintient le Snapshot, et expose l'API HTTP/WebSocket aux clients.

**dcs-client**
Outil Python en ligne de commande avec trois modes : `--tui` (Textual), `--web` (Leaflet), `--mcp` (MCP server). Se connecte à `dcs-serve` via HTTP/WebSocket — peut tourner sur une machine différente.

**Lua bridge**
Script Lua injecté dans la mission DCS. Ouvre et maintient la connexion TCP sortante vers `dcs-serve`. Envoie les Events et le Snapshot complet toutes les 5 secondes. Exécute les Commands reçues.

## Protocole TCP

**Command**
Message envoyé par `dcs-serve` vers le Lua bridge, demandant l'exécution d'une action dans DCS. Contient un `id` unique pour la corrélation. Format : `{ "id": "...", "action": "exec"|"spawn", "payload": {...} }`.

**Response**
Réponse du Lua bridge à une Command. Contient le même `id` que la Command. Format : `{ "id": "...", "result": "...", "error": null }`.

**Event**
Message spontané envoyé par le Lua bridge vers `dcs-serve` sans être sollicité. Exemples : position d'unité, destruction, spawn. Format : `{ "type": "event", "name": "...", "data": {...} }`.

**Correlation ID**
Identifiant unique (`id`) présent dans chaque Command et sa Response correspondante. Permet à `dcs-serve` d'associer une réponse TCP à la requête HTTP en attente.

**Full Refresh**
Message Lua bridge → `dcs-serve` envoyé toutes les 5 secondes contenant l'état complet de toutes les unités de la mission. Utilisé pour resynchroniser le Snapshot après d'éventuels Events manqués.

## État côté serve

**Snapshot**
Photo en mémoire de l'état courant de la mission DCS maintenue par `dcs-serve`. Mise à jour par les Events et remplacée intégralement par le Full Refresh. Sert les requêtes `GET /api/units` instantanément.

**Stale**
Qualifie un Snapshot dont le dernier Full Refresh date de plus de N secondes (configurable). `GET /api/units` inclut `stale: true` et `last_updated` dans ce cas.

## Coordonnées

**position_dcs**
Coordonnées dans le système natif DCS : `x` et `z` pour le plan horizontal, `y` pour l'altitude absolue. Calculées par DCS, transmises telles quelles par le Lua bridge.

**position_geo**
Coordonnées géographiques lat/lon calculées par le Lua bridge via `coord.LOtoLL()` (API DCS native). Fiables pour tous les théâtres sans logique de conversion côté Python.

**altitude_agl**
Altitude au-dessus du sol (Above Ground Level) en mètres, calculée par le Lua bridge via `land.getHeight()`.

## Sécurité

**API Key**
Clé d'authentification requise pour toutes les requêtes vers `dcs-serve`. Passée en header `X-API-Key`. Générée automatiquement au premier démarrage et stockée dans `dcs-serve.yaml`.

## Interfaces client

**TUI**
Interface terminal interactive (Textual) exposée par `dcs-client --tui`. Affiche le Snapshot et permet d'exécuter du Lua arbitraire.

**WebUI**
Interface web statique (HTML/JS + Leaflet) servie localement par `dcs-client --web`. Affiche les unités sur une carte en temps réel via WebSocket.

**MCP server**
Serveur MCP exposé par `dcs-client --mcp`. Permet aux agents IA de piloter DCS via quatre outils : `exec_lua`, `get_units`, `spawn_unit`, `get_mission_info`.

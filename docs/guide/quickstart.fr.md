# Démarrage rapide

## 1. Lancer dcs-serve

```bash
dcs-serve
```

Au premier lancement, `dcs-serve.yaml` est créé avec une clé API générée automatiquement. Notez cette clé pour la copier dans `dcs-client.yaml`.

```
INFO  TCP server listening on 0.0.0.0:7777
INFO  HTTP server listening on 0.0.0.0:8080
INFO  API key: AbCdEfGhIjKlMnOpQrStUvWxYz123456
```

## 2. Injecter le script Lua

Copiez `dcs-bridge.lua` sur votre serveur DCS et injectez-le dans la mission (voir [Prérequis](prerequisites.md)).

Lancez DCS World. Dans la console de dcs-serve, vous devriez voir :

```
INFO  DCS connected from 127.0.0.1
INFO  Snapshot ready — 42 units
```

## 3. Lancer un client

=== "Interface web"

    ```bash
    dcs-client web
    ```

    Le navigateur s'ouvre automatiquement sur `http://127.0.0.1:8081` avec la carte Leaflet.

=== "TUI terminal"

    ```bash
    dcs-client tui
    ```

    Le tableau des unités s'affiche en temps réel avec un REPL Lua intégré.

=== "Serveur MCP (agents IA)"

    Configurez votre agent IA (Claude, etc.) pour utiliser le serveur MCP :

    ```bash
    dcs-client mcp
    ```

    Les outils disponibles : `exec_lua`, `get_units`, `spawn_unit`, `get_mission_info`.

## Configuration réseau

Si `dcs-serve` et les clients tournent sur des machines différentes, éditez `dcs-client.yaml` :

```yaml
host: "192.168.1.100"   # adresse IP de la machine dcs-serve
port: 8080
api_key: "votre-cle-api"
```

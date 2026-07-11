# Référence CLI

## dcs-serve

```
Usage: dcs-serve [OPTIONS]

Options:
  --config PATH  Chemin vers dcs-serve.yaml  [défaut : dcs-serve.yaml]
  --help         Afficher ce message et quitter
```

Lance le serveur TCP (pour la connexion Lua) et le serveur HTTP/WebSocket (pour les clients).

## dcs-client

```
Usage: dcs-client COMMAND [OPTIONS]

Commands:
  tui   Interface terminal Textual
  web   Serveur HTTP local avec carte Leaflet
  mcp   Serveur MCP stdio pour agents IA
```

### dcs-client tui

```
Usage: dcs-client tui [OPTIONS]

Options:
  --config PATH  Chemin vers dcs-client.yaml  [défaut : dcs-client.yaml]
  --help         Afficher ce message et quitter
```

Lance l'interface terminal avec tableau des unités en temps réel et REPL Lua.

**Raccourcis clavier dans le TUI :**

| Touche | Action |
|---|---|
| `Entrée` | Exécuter la commande Lua |
| `Ctrl+C` | Quitter |

### dcs-client web

```
Usage: dcs-client web [OPTIONS]

Options:
  --config PATH      Chemin vers dcs-client.yaml         [défaut : dcs-client.yaml]
  --web-host TEXT    Adresse d'écoute du serveur HTTP local  [défaut : 127.0.0.1]
  --web-port INT     Port du serveur HTTP local (0 = valeur web_port du config)  [défaut : 0]
  --help             Afficher ce message et quitter
```

Lance un serveur HTTP local et ouvre la carte Leaflet dans le navigateur. La carte se
connecte à `dcs-serve` avec les valeurs `host`, `port` et `api_key` de `dcs-client.yaml`
(exposées au navigateur via `GET /config.json`), sans aucune URL à modifier à la main.

### dcs-client mcp

```
Usage: dcs-client mcp [OPTIONS]

Options:
  --config PATH  Chemin vers dcs-client.yaml  [défaut : dcs-client.yaml]
  --help         Afficher ce message et quitter
```

Lance le serveur MCP sur `stdio`. À utiliser avec un agent IA compatible MCP.

**Outils MCP exposés :**

| Outil | Description |
|---|---|
| `exec_lua(code, timeout?)` | Exécute du code Lua dans DCS World |
| `get_units()` | Retourne la liste des unités actives |
| `spawn_unit(group_def)` | Fait apparaître un groupe d'unités |
| `get_mission_info()` | Retourne les informations de la mission (théâtre…) |

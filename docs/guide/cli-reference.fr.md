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

Lance un serveur HTTP local et ouvre la carte Leaflet dans le navigateur. Le serveur web
lit `host`, `port` et `api_key` depuis `dcs-client.yaml` ; il conserve le token côté
serveur et n'expose que `host`/`port` via `GET /config.json`, en fournissant au
navigateur des tickets WebSocket éphémères via `POST /ws-ticket` (aucun credential dans
le navigateur).

### dcs-client mcp

```
Usage: dcs-client mcp [OPTIONS]

Options:
  --config PATH  Chemin vers dcs-client.yaml  [défaut : dcs-client.yaml]
  --help         Afficher ce message et quitter
```

Lance le serveur MCP sur `stdio`. À utiliser avec un agent IA compatible MCP.

**Outils MCP exposés** (un jeu réduit et fixe — le client ne porte aucun savoir
de domaine et relaie le catalogue capability-aware, ADR-0005) :

| Outil | Description |
|---|---|
| `list_catalog()` | Liste les actions sémantiques disponibles pour la mission en cours |
| `search_catalog(query)` | Recherche dans les actions et la longue traîne (types DCS, keyphrases VEAF) |
| `describe_action(name)` | Décrit les paramètres et valeurs valides d'une action |
| `run_action(name, args?, backend?)` | Exécute une action sémantique (spawn, smoke, remove, run_keyphrase…) |
| `get_units()` | Retourne la liste des unités actives |
| `capabilities()` | Retourne les frameworks détectés dans la mission |
| `exec_lua(code, timeout?)` | Exécute du Lua brut (nécessite le rôle `superuser`) |

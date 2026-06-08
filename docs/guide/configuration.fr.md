# Configuration

## dcs-serve.yaml

Ce fichier configure le serveur dcs-serve. Il est créé automatiquement au premier lancement si absent.

```yaml
# Adresse et port TCP sur lesquels dcs-serve écoute les connexions depuis DCS
tcp_host: "0.0.0.0"
tcp_port: 9999

# Adresse et port HTTP/WS pour l'API REST et WebSocket
http_host: "0.0.0.0"
http_port: 8080

# Clé API (générée automatiquement au premier lancement si vide)
api_key: ""

# Timeout par défaut des commandes Lua, en secondes
default_timeout: 10.0

# Seuil de péremption du snapshot : si aucune mise à jour n'est reçue
# depuis DCS pendant ce délai, l'API renvoie 503 avec {"stale": true}
stale_threshold: 15.0
```

### Variables importantes

| Paramètre | Défaut | Description |
|---|---|---|
| `tcp_port` | `9999` | Port TCP que le script Lua doit cibler |
| `http_port` | `8080` | Port de l'API REST et WebSocket |
| `api_key` | *(auto)* | Clé à transmettre aux clients (`X-API-Key`) |
| `default_timeout` | `10.0` | Timeout des commandes `exec` et `spawn` |
| `stale_threshold` | `15.0` | Délai avant de marquer le snapshot comme périmé |

## dcs-client.yaml

Ce fichier configure les clients (TUI, web, MCP).

```yaml
# Adresse de dcs-serve
host: "127.0.0.1"
port: 8080

# Clé API (doit correspondre à celle de dcs-serve.yaml)
api_key: "votre-cle-api"
```

Le fichier est recherché dans le répertoire courant ou via l'option `--config`.

## Script Lua

Le script `dcs-bridge.lua` se connecte à `dcs-serve` via TCP. Les paramètres de connexion se trouvent en tête du fichier :

```lua
local HOST = "127.0.0.1"   -- adresse de dcs-serve
local PORT = 9999           -- doit correspondre à tcp_port dans dcs-serve.yaml
```

Modifiez ces valeurs si DCS World et `dcs-serve` tournent sur des machines différentes.

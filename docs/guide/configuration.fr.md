# Configuration

## dcs-serve.yaml

Ce fichier configure le serveur dcs-serve. Il est créé automatiquement au premier lancement si absent.

```yaml
# Adresse et port TCP sur lesquels dcs-serve écoute les connexions depuis DCS
tcp_host: "0.0.0.0"
tcp_port: 7777

# Adresse et port HTTP/WS pour l'API REST et WebSocket
http_host: "0.0.0.0"
http_port: 8080

# Token Bearer (généré automatiquement au premier lancement si vide). Conservé
# comme token superuser pendant la transition vers le modèle par rôles
# (voir dcs-tokens.yaml).
api_key: ""

# Chemin du magasin de tokens porteurs de rôle (optionnel)
tokens_file: "dcs-tokens.yaml"

# Timeout par défaut des commandes Lua, en secondes
default_timeout: 10.0

# Seuil de péremption du snapshot : si aucune mise à jour n'est reçue
# depuis DCS pendant ce délai, l'API renvoie 503 avec {"stale": true}
stale_threshold: 15.0
```

### Variables importantes

| Paramètre | Défaut | Description |
|---|---|---|
| `tcp_port` | `7777` | Port TCP que le script Lua doit cibler |
| `http_port` | `8080` | Port de l'API REST et WebSocket |
| `api_key` | *(auto)* | Token Bearer durable ; utilisé comme token `superuser` (ADR-0005) |
| `tokens_file` | `dcs-tokens.yaml` | Magasin de tokens porteurs de rôle (optionnel) |
| `default_timeout` | `10.0` | Timeout des commandes `exec` et `spawn` |
| `stale_threshold` | `15.0` | Délai avant de marquer le snapshot comme périmé |

### dcs-tokens.yaml (optionnel)

Les tokens porteurs de rôle remplacent la clé API unique (ADR-0005). Chaque token
porte un rôle (`observer`/`pilot`/`operator`/`administrator`/`superuser`, ou un
niveau VEAF numérique) et, en option, `label`/`ucid`/`expiry` :

```yaml
- token: "observer-token"
  role: observer
  label: "tableau de bord lecture seule"
- token: "ops-token"
  role: operator
  label: "opérateur de mission"
```

Les clients REST envoient leur token via `Authorization: Bearer <token>`. Si ce
fichier est absent, l'`api_key` ci-dessus continue de fonctionner comme token
`superuser`.

## dcs-client.yaml

Ce fichier configure les clients (TUI, web, MCP).

```yaml
# Adresse de dcs-serve
host: "127.0.0.1"
port: 8080

# Token Bearer (doit correspondre à un token accepté par dcs-serve)
api_key: "votre-token"

# Port local de la carte Leaflet du client web
web_port: 8081
```

Le fichier est recherché dans le répertoire courant ou via l'option `--config`.
`api_key` est le token Bearer durable du client ; son rôle détermine quelles
actions aboutissent (appliqué par dcs-serve).

`dcs-client web` conserve ce token **côté serveur** et ne l'expose jamais au
navigateur (ADR-0005) : `GET /config.json` ne renvoie que `host`/`port`, et la page
Leaflet ouvre son WebSocket avec un ticket éphémère à usage unique obtenu via le
proxy `POST /ws-ticket` du serveur web. Aucun credential n'apparaît dans la page,
une URL ou `/config.json`. `web_port` est le port local sur lequel la carte est
servie.

!!! note "Aucun credential dans le navigateur"
    Le token durable reste sur le serveur web ; le navigateur ne reçoit que des
    tickets WebSocket éphémères. Le client web écoute sur `127.0.0.1` par défaut ;
    ne passez `--web-host 0.0.0.0` que sur un réseau de confiance.

## Script Lua

Le script `dcs-bridge.lua` se connecte à `dcs-serve` via TCP. Les paramètres de connexion se trouvent en tête du fichier :

```lua
local HOST = "127.0.0.1"   -- adresse de dcs-serve
local PORT = 7777           -- doit correspondre à tcp_port dans dcs-serve.yaml
```

Modifiez ces valeurs si DCS World et `dcs-serve` tournent sur des machines différentes.

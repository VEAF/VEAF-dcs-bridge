# Installation

## Via les binaires GitHub Releases (recommandé)

Téléchargez la dernière archive depuis la page [GitHub Releases](https://github.com/VEAF/dcs-bridge/releases) :

```
dcs-bridge-x.y.z.zip
├── dcs-serve.exe
├── dcs-client.exe
└── dcs-bridge.lua
```

Extrayez l'archive dans le dossier de votre choix, par exemple `C:\dcs-bridge\`.

### Vérification

```powershell
.\dcs-serve.exe --help
.\dcs-client.exe --help
```

## Via pip

```bash
pip install dcs-bridge
dcs-serve --help
dcs-client --help
```

## Via Poetry (développement)

```bash
git clone https://github.com/VEAF/dcs-bridge.git
cd dcs-bridge
poetry install
poetry run dcs-serve --help
```

## Script Lua

Copiez `dcs-bridge.lua` sur la machine qui héberge DCS World et injectez-le selon la méthode décrite dans les [Prérequis](prerequisites.md).

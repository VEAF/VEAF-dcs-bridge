# Installation

## Via GitHub Releases binaries (recommended)

Download the latest archive from the [GitHub Releases](https://github.com/VEAF/dcs-bridge/releases) page:

```
dcs-bridge-x.y.z.zip
├── dcs-serve.exe
├── dcs-client.exe
└── dcs-bridge.lua
```

Extract the archive to a folder of your choice, e.g. `C:\dcs-bridge\`.

### Verification

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

## Via Poetry (development)

```bash
git clone https://github.com/VEAF/dcs-bridge.git
cd dcs-bridge
poetry install
poetry run dcs-serve --help
```

## Lua script

Copy `dcs-bridge.lua` to the machine hosting DCS World and inject it using the method described in [Prerequisites](prerequisites.md).

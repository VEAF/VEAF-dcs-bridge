# Prerequisites

## DCS World

dcs-bridge requires **DCS World** installed on the mission server (Open Beta or Stable).

The Lua script `dcs-bridge.lua` must be injected into each mission. Two methods are available:

### Method 1 — MissionScripting.lua (persistent)

Add the following line to `DCS World/Scripts/MissionScripting.lua`:

```lua
dofile([[C:\path\to\dcs-bridge.lua]])
```

This method loads the bridge for **all missions** on this server.

### Method 2 — DO SCRIPT FILE trigger (per mission)

In the DCS mission editor, create a trigger:

- **Condition**: Mission Start
- **Action**: DO SCRIPT FILE → select `dcs-bridge.lua`

This method activates the bridge only for the specific mission.

## VMCT v6 (recommended)

[VMCT v6](https://veaf.github.io/documentation/dev/) is the VEAF-recommended tool for automatically injecting `dcs-bridge.lua` into missions without modifying `MissionScripting.lua`.

See the [VEAF documentation](https://veaf.github.io/documentation/dev/) for VMCT installation and configuration instructions.

## dcs-serve host machine

- **OS**: Windows 10/11, Linux, or macOS
- **Python**: 3.11 or higher (only if installing via `pip` or Poetry)
- **Network**: the DCS server must be able to reach `dcs-serve` on the configured TCP port (default: 7777)

# Prerequisites

## DCS World

dcs-bridge requires **DCS World** installed on the mission server (Open Beta or Stable).

## Lift the script sanitisation (mandatory)

`dcs-bridge.lua` talks to `dcs-serve` over a TCP socket, which it obtains with
`require("socket")`. By default DCS **sanitises** mission scripting: before any mission
script runs, `MissionScripting.lua` strips `require` along with the `os`, `io` and `lfs`
modules. On an untouched DCS installation the bridge therefore fails on its first line
and nothing ever connects.

This is a one-time change to your DCS installation, and it is needed **whichever
injection method you choose below** — including VMCT, which automates injecting the
script but does not lift the sandbox.

**With DCS closed**, open `DCS World/Scripts/MissionScripting.lua` and remove the
sanitisation: delete or comment out everything below the line that starts with

```lua
local function sanitizeModule(name)
```

!!! warning "Understand what you are allowing"
    Lifting the sanitisation lets **any** mission script running on this machine read and
    write files and start programs. Only do this on a server whose missions you control,
    and never in order to open a `.miz` from an untrusted source.

!!! note "Reapply after every DCS update"
    A DCS update restores the original `MissionScripting.lua`, and the bridge silently
    stops connecting — look for the `require` error in `DCS.log`. Redo this change after
    each update.

Several widely used DCS scripts need the same modification (SRS's
DCS-SimpleTextToSpeech, for one), so it may already be in place on your server.

## Injecting the script

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

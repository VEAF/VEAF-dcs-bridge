# 03 — Document the mandatory `MissionScripting.lua` sanitisation lift

Status: ✅ done
Type: docs

## Why this surfaced

Found while writing `RELEASE_NOTES.md` for ticket 02, checking that every stated
prerequisite was real. `docs/guide/prerequisites.{en,fr}.md` documented **only** how to
inject `dcs-bridge.lua` (three methods, VMCT recommended) and never mentioned the DCS
script sanitisation.

But `src/lua/dcs-bridge.lua:45` does:

```lua
local socket = require("socket")
```

and stock DCS strips `require` (along with `os`, `io`, `lfs`) in `MissionScripting.lua`
before any mission script runs. So a helper following the documentation on an untouched
DCS installation gets nothing — the bridge dies on its first line and never connects.

This mattered for ticket 02 specifically: the whole point of publishing the release is
that helpers can run the map-capture kit. Shipping it with the one mandatory DCS-side
step undocumented would have made it the first failure everybody hit.

## What was unclear, and how it was resolved

The exact procedure was not written from memory. `DCS-SimpleTextToSpeech.lua` — a
community script VEAF already ships inside `veaf-mission-creation-tools` — documents the
ecosystem-standard instruction, which the new section follows: with DCS closed, remove
everything below the line starting `local function sanitizeModule(name)`, and **reapply
after every DCS update**.

## Change

New `## Lift the script sanitisation (mandatory)` section in
`docs/guide/prerequisites.en.md` and `prerequisites.fr.md`, placed **before** the
injection methods (it applies whichever one is chosen) with the existing methods regrouped
under an `## Injecting the script` heading. It covers:

- why it is needed (`require("socket")`) and the symptom when it is missing;
- that VMCT automates *injection*, not the sandbox — it does not remove this step;
- the procedure, with DCS closed;
- a `warning` admonition on what lifting the sandbox actually allows;
- a `note` admonition that a DCS update silently reverts it (look for the `require`
  error in `DCS.log`);
- that other common scripts need the same change, so it may already be done.

Matches the admonition style already used in `docs/guide/configuration.{en,fr}.md`.

## Definition of Done

- A reader following the prerequisites from a stock DCS install reaches a working bridge.
- EN and FR in sync.

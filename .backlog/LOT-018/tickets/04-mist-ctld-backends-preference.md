# 04 — MIST & CTLD backends + hybrid backend preference

Status: ⬜ ready
Type: feat

Ref: [ADR-0005](../../../docs/adr/0005-capability-aware-bridge.md) — decisions *Execution*, *Backend preference*.

## What to build

- **MIST adapter** (`mist.dynAdd`) and **CTLD v2 adapter** (manager API:
  `CTLDCrateManager:spawnCrateAtPoint`, `CTLDSceneManager:playSceneAtPos` for FOB/FARP,
  `CTLDTroopManager:spawnGroupAtPoint`, `ctld.spawnFOB`). Player-bound CTLD actions
  (helo load/unload) are excluded (no player context).
- **Hybrid preference**: global default `VMCT > CTLD > MIST > DCS`, overridable per action
  in the registry; optional client `backend=` override.

## Acceptance criteria

- [ ] With several backends present, the bridge picks per preference; `backend=` forces one.
- [ ] `spawn_farp` resolves to CTLD scene / DCS static per availability.
- [ ] Adapters' emitted Lua asserted in unit tests. Quality gate green.

## Blocked by
Tickets 01, 03.

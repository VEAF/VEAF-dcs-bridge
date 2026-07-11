# 02 — Capability detection (handshake, version lockstep, cache)

Status: ✅ done
Type: feat

Ref: [ADR-0005](../../../docs/adr/0005-capability-aware-bridge.md) — decision *Capability detection*.

## What to build

- **Lua**: at the Lua↔serve handshake, probe and announce loaded frameworks + versions
  (`veaf.BuildVersion`, `ctld.VERSION or ctld.Version`, `mist` presence/version, DCS
  always). Re-announce on reconnect / mission change.
- **serve**: cache the capability set; expose it (`GET /api/capabilities`). Match each
  framework against the **exact version this build targets** (lockstep); a mismatch marks
  the capability absent.

## Acceptance criteria

- [ ] serve knows, per mission, which of {dcs, mist, ctld, veaf} are present at the
      expected version, refreshed on reconnect/mission change, never re-probed per action.
- [ ] Version mismatch → capability reported absent (logged).
- [ ] Unit tests for the matching/caching logic. Quality gate green.

## Blocked by
Ticket 01 (exec/handshake plumbing).

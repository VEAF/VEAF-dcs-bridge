# 05 — VEAF/VMCT backend

Status: ⬜ ready
Type: feat

Ref: [ADR-0005](../../../docs/adr/0005-capability-aware-bridge.md) — decision *Execution*.

## What to build

- **VEAF adapter** driving `veafCommands.execute(pos, text, coalition, nil, nil)` — the
  adapter **composes the keyphrase string** per module grammar (no typed per-field API in
  VEAF).
- Catalogue the **static default shortcut list** shipped with VMCT (helps specialise the
  adapter). Per-mission custom aliases are **out of scope** (ADR open question).
- Propagate the resolved role→VEAF level (do not blanket-`bypassSecurity`).

## Acceptance criteria

- [ ] A `run_keyphrase`/`spawn` routed to VEAF produces the correct command string and
      executes without a map marker.
- [ ] Default shortcuts are discoverable via `search_catalog`.
- [ ] Adapter string-composition unit-tested. Quality gate green.

## Blocked by
Tickets 03, 04.

# Lot LOT-018 — Implement the capability-aware bridge (ADR-0005)

Status: ⬜ ready

**Effort**: XL (epic)
**Branch**: (not started)

## Problem Statement

dcs-bridge is a low-level passthrough (`exec_lua`, MIST-only `spawn`, single API key).
[ADR-0005](../../docs/adr/0005-capability-aware-bridge.md) decides to turn it into a
**capability-aware semantic-action façade**: it detects the frameworks loaded in the
running mission (DCS/MIST/CTLD/VMCT), exposes high-level actions filtered by capability,
routes each to the best backend, and gates everything with a role-based security model
aligned on VEAF levels.

## Scope

This is an **epic**: it will ship as **several PRs**, one per ticket below (a deliberate
exception to "one PR per lot" — each phase may also be promoted to its own lot). Tickets
are ordered by dependency; ticket 01 is a vertical tracer-bullet that already replaces
the MIST-only `spawn` limitation end-to-end.

All design decisions and rationale live in ADR-0005 — tickets reference it rather than
restating it. Open questions from the ADR (spatial resolution, per-mission custom VEAF
aliases, feature-detection fallback, catalogue-generation pipeline) are resolved as they
are reached, not up front.

## Tickets (phases)

1. Tracer-bullet — semantic `spawn` end-to-end via the DCS-native backend.
2. Capability detection (handshake, version lockstep, cache) + `/api/catalog`.
3. Action registry + parameterised verbs + `search_catalog`/`describe`.
4. MIST & CTLD (v2) backends + hybrid backend preference.
5. VEAF/VMCT backend (`veafCommands.execute` + static default shortcuts).
6. Security — roles + tokens + per-action minimum-role enforcement.
7. Transport — Bearer (REST) + ephemeral WS ticket; WEB proxy; kill the key-in-URL leak.
8. Clients — MCP catalogue mapping; TUI/WEB catalogue presentation.

## User Stories

1. As a client, I ask for a high-level action (`spawn` a FARP) and the bridge performs
   it with whatever framework the mission has, without me knowing DCS internals.
2. As an operator, I hand out scoped tokens (observer/pilot/operator/administrator/
   superuser) so a machine client gets exactly the capabilities I intend.

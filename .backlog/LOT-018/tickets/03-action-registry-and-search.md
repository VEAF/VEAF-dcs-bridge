# 03 — Action registry, parameterised verbs, `search_catalog`

Status: ⬜ ready
Type: feat

Ref: [ADR-0005](../../../docs/adr/0005-capability-aware-bridge.md) — decisions *Catalogue = union*, *Granularity*.

## What to build

- A **registry** where each action declares: name, arg schema, supported backends +
  per-action preference override, minimum role (placeholder until ticket 06), and whether
  it is portable or backend-specific.
- **Parameterised verbs** (`spawn`, `remove`, `smoke`, `run_keyphrase`, …) with the "what"
  as a parameter; the long tail (DCS types, default VEAF keyphrases) held as **queryable
  data**, not tools.
- `GET /api/catalog` (filtered by detected capabilities) + `search_catalog(query)` /
  `describe(action)`.

## Acceptance criteria

- [ ] Catalogue returned is the **union** filtered by capabilities; flagship actions are
      catalogue entries of a generic verb, not dedicated actions.
- [ ] `search_catalog`/`describe` let a client discover valid `kind`/keyphrase values
      without loading the whole tail.
- [ ] Unit tests on filtering + search. Quality gate green.

## Blocked by
Ticket 02.

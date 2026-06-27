---
status: accepted
---

# Backlog restructure to `.backlog/` per-lot directories

The backlog lived in a single monolithic `BACKLOG.md` (~24 KB). With one branch and
one PR per lot (CLAUDE.md §8), the monolith was a recurring merge-conflict surface,
and loading the whole file cost agent context on every task. We also wanted to drive
the backlog with the Matt Pocock engineering skills (`to-prd`, `to-issues`,
`triage`), which are issue-tracker-agnostic and configured per repo (no fork
required).

## Decision

Adopt a per-lot `.backlog/` structure:

- **Active lots** are directories — `.backlog/<LOT-ID>/PRD.md` plus one
  `tickets/<NN>-<slug>.md` per ticket.
- **Completed lots** are compact `.backlog/archive/<LOT-ID>.md` files (ticket table
  preserved, not split).
- A single `Status:` vocabulary (⬜ ready · 🔄 in-progress · 🧑 waiting-human ·
  ✅ done · 🚫 wontfix) maps onto Matt's triage roles.
- The Matt Pocock skills stay globally installed and unmodified; per-repo config
  under `docs/agents/*` plus an `## Agent skills` block in `CLAUDE.md` adapts them
  to this backlog.
- The lot index `.backlog/README.md` is maintained by hand (no generator script).
- `.backlog/` is a dotfolder: internal working state, excluded from the published
  MkDocs site.

This repo has no `ROADMAP.md`; `.backlog/README.md` is the single source of truth
for both sequencing and scope + status.

## Migration

At adoption time every lot (LOT-001 → LOT-011) was already shipped, so the whole
monolith was migrated directly into `.backlog/archive/<LOT-ID>.md` compact files —
no active lot directories were created. The two Typer entry-point bug fixes
(previously listed "HORS LOT", named LOT-011 in the CHANGELOG) became
`archive/LOT-011.md`. `BACKLOG.md` was then deleted.

## Consequences

- No more backlog merge conflicts; agents load only the relevant lot.
- `to-prd` / `to-issues` work against the local backlog with no upstream fork.
- One-time migration cost; archived shipped lots are kept compact, not split.

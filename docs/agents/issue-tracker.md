# Issue tracker: local `.backlog/` directory

Lots, PRDs, and tickets for this repo live as markdown under `.backlog/`.
`.backlog/` is internal working state — a dotfolder, excluded from the published
MkDocs site (`docs_dir` is `docs/`).

## Conventions

- One active lot per directory: `.backlog/<LOT-ID>/`
- The PRD is `.backlog/<LOT-ID>/PRD.md` (Matt's PRD template; no separate `## Goal`)
- Tickets are `.backlog/<LOT-ID>/tickets/<NN>-<slug>.md`, numbered from `01` in dependency order
- Status is a `Status:` line near the top of each PRD/ticket file (see `triage-labels.md`)
- The lot index (Active + Archived tables of every lot + status) is `.backlog/README.md`, maintained by hand — there is no generator script
- One feature branch and one PR per lot, targeting `develop`
- Completed lots are moved to `.backlog/archive/<LOT-ID>.md` (compact, ticket table preserved, not split) once closed > 3 days

## When a skill says "publish to the issue tracker"

- A PRD → write `.backlog/<LOT-ID>/PRD.md`, create the directory if needed, and add a row to the **Active lots** table in `.backlog/README.md`.
- An issue → write `.backlog/<LOT-ID>/tickets/<NN>-<slug>.md`.
- New artifacts are created at `Status: ⬜ ready`.

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user normally passes the lot ID or ticket
path directly.

## Archiving

When a lot has been closed (`✅ done`) for more than 3 days, compact it into a single
`.backlog/archive/<LOT-ID>.md` (a header + one ticket table), delete the
`.backlog/<LOT-ID>/` directory, and move its row from **Active lots** to
**Archived lots** in `.backlog/README.md`.

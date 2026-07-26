# 02 — Publish the first release (so `dcs-serve.exe` is downloadable)

Status: 🧑 waiting-human
Type: chore

## Context

`gh release list` on this repo returns nothing: no release has ever been published, so
`dcs-serve.exe` exists only on machines that build it. The release workflow is already
written and, on a `published-v*` tag, does the right things:

1. lint / type-check / test,
2. `pyinstaller dcs-serve.spec` + `dcs-client.spec`,
3. zip `dcs-serve.exe` + `dcs-client.exe` (+ `dcs-bridge.lua`) as `dcs-bridge-<version>.zip`,
4. create the GitHub Release with `RELEASE_NOTES.md` and move `published-latest`.

It has simply never been triggered.

## Blocked by

Ticket 01 — publishing before the `__main__` fix would ship a **broken** `dcs-serve.exe`
(starts and exits). Do 01 first.

## Finding — `RELEASE_NOTES.md` does not exist

Checked during ticket 01: the file has **never been committed** (`git log --all --
RELEASE_NOTES.md` is empty), yet `release.yml` passes `body_path: RELEASE_NOTES.md` to
`softprops/action-gh-release`. The release job would fail at the publish step. It must be
authored first — via the project's own `/release-notes` procedure
(`.claude/commands/release-notes.md`), which also picks the target version, replaces the
`[Unreleased]` CHANGELOG header with `[x.y.z] — YYYY-MM-DD`, and bumps `pyproject.toml`.

Note `CHANGELOG.md`'s `[Unreleased]` section still holds **every** change since the
project started (no release was ever cut), so the notes must be curated, not copied.

## Tasks

- [x] Author `RELEASE_NOTES.md` (it did not exist — see the finding above). Written for a
      server operator / mission maker, not a project developer: what the download
      contains, how to start, what the bridge does, and how to migrate a pre-release
      source checkout (Bearer replacing `X-API-Key`, WS tickets, the reworked MCP tool
      set). Validated by David.
- [x] Document the sanitisation prerequisite — see ticket 03, opened because writing the
      "Requirements" section exposed that it was missing.
- [x] Confirm the version source of truth: `pyproject.toml` → `1.0.0`, CHANGELOG
      `[Unreleased]` → `[1.0.0] — 2026-07-26`. Tag to push: `published-v1.0.0`.
- [ ] **David pushes the tag** (irreversible, triggers the publish workflow):
      `git tag published-v1.0.0 && git push origin published-v1.0.0`, once this release
      PR is merged into `develop`.
- [ ] Watch the workflow — note it now runs the ticket-01 smoke tests on the built exes
      before publishing, so a broken build fails instead of shipping.
- [ ] Check the release carries `dcs-bridge-<version>.zip` and that the zip contains
      `dcs-serve.exe`, `dcs-client.exe` and `dcs-bridge.lua`
      (VMCT's kit job looks up `dcs-serve.exe` **and** `dcs-bridge.lua` by basename).
- [ ] Download the asset and double-click `dcs-serve.exe` once, as a maker would.

## Downstream effect

VMCT's release workflow has a `kit` job that runs
`gh release download --repo VEAF/VEAF-dcs-bridge --pattern "dcs-bridge-*.zip"`
(best-effort). Once this release exists, the next VMCT release automatically bundles the
bridge server into `veaf-map-capture-kit-<version>.zip` — no change needed on that side.

## Definition of Done

- A published release here, asset verified, exe manually launched once.

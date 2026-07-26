# 02 — Publish the first release (so `dcs-serve.exe` is downloadable)

Status: ✅ done
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
- [x] Tag pushed: `published-v1.0.0` on `develop` (61492f7), 2026-07-26.
- [x] Workflow watched — [run 30214696048](https://github.com/VEAF/VEAF-dcs-bridge/actions/runs/30214696048)
      succeeded on its **first ever execution**. Both ticket-01 smoke tests passed on a
      clean runner: `dcs-serve.exe` bound 7777 + 8080 within the timeout and its process
      tree terminated; `dcs-client.exe --help` listed its subcommands.
- [x] Asset verified by downloading it with the same command VMCT's kit job uses
      (`gh release download --repo VEAF/VEAF-dcs-bridge --pattern "dcs-bridge-*.zip"`).
      `dcs-bridge-1.0.0.zip` (45.9 MB) extracts to exactly the three expected files at the
      archive root, so the basename lookups resolve:

      | File | Size |
      |---|---|
      | `dcs-serve.exe` | 20 970 979 |
      | `dcs-client.exe` | 27 838 185 |
      | `dcs-bridge.lua` | 13 575 |

- [x] Ran the **downloaded** `dcs-serve.exe` as a maker would — this checks the
      CI-produced binary, not a local build. It generated `dcs-serve.yaml` with a fresh
      api_key on first start, logged
      `TCP server listening on ('127.0.0.1', 7777)` and
      `Uvicorn running on http://0.0.0.0:8080`, and shut down cleanly.

## Downstream effect

VMCT's release workflow has a `kit` job that runs
`gh release download --repo VEAF/VEAF-dcs-bridge --pattern "dcs-bridge-*.zip"`
(best-effort). Once this release exists, the next VMCT release automatically bundles the
bridge server into `veaf-map-capture-kit-<version>.zip` — no change needed on that side.

## Definition of Done

- A published release here, asset verified, exe manually launched once.

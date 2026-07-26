# LOT-020 — `dcs-serve.exe` never starts (PyInstaller entry point) + first release

Status: ✅ done

## Context (handoff)

While building a **map-capture kit** in VEAF-Mission-Creation-Tools (lot
`FEAT-AIRDROMES-RUNTIME-SOURCE`), we needed `dcs-serve.exe` for non-developers. Two
blockers surfaced in this repo:

1. **The packaged `dcs-serve.exe` does nothing.** Double-clicking it (or running it from
   a terminal) exits immediately, silently, with code 0 — no server, no log, nothing
   listening on 7777/8080. Reproduced on Windows with a fresh
   `pyinstaller dcs-serve.spec` build.
   **Root cause**: `dcs-serve.spec` bundles `src/dcs_bridge/serve/app.py` **as the
   script**, but that module has no `if __name__ == "__main__":` block. PyInstaller
   therefore imports/executes the module — defining `_cli`, `main`, `_serve` — and exits
   without ever calling `main()`. The Poetry console-script (`dcs-serve = ...app:main`)
   masked the gap, so `poetry run dcs-serve` always worked.
   **Fix already applied locally** (uncommitted, see below): a `__main__` guard calling
   `main()`. Verified: the rebuilt exe listens on `('127.0.0.1', 7777)` + `0.0.0.0:8080`,
   accepts a DCS connection, and served a real `POST /api/exec` capture end-to-end.
2. **No release has ever been published**, so `dcs-serve.exe` is not downloadable
   anywhere. The workflow (`.github/workflows/release.yml`) is written and looks correct
   — it builds both exes and uploads `dcs-bridge-<version>.zip` — it has simply never
   been triggered by a `published-v*` tag.

## Why it matters now

VMCT's release workflow gained a `kit` job that downloads
`dcs-bridge-*.zip` from **this repo's** latest release to bundle `dcs-serve.exe` into
`veaf-map-capture-kit-<version>.zip`. That step is best-effort: until a release exists
here, the kit ships **without** the bridge server, and helpers cannot capture anything.

## ✅ Uncommitted working-tree state — resolved

Handled as described: `serve/app.py` committed in ticket 01, `capabilities.py` reverted
(never committed), and `build_pyi/` + `test-mission/` gitignored (plus `site/`, the MkDocs
output, which turned out not to be ignored either).

The original note, for the record. **The two files were not equivalent:**

| File | What it is | Action |
|---|---|---|
| `src/dcs_bridge/serve/app.py` | The `__main__` fix above | **Commit it** (ticket 01) |
| `src/dcs_bridge/serve/capabilities.py` | Hardcodes `mist`/`ctld`/`veaf` versions to one specific running mission, self-labelled `TEMPORARY … DO NOT COMMIT` | **Do NOT commit** — revert it, and treat loose version matching as its own lot |

Also untracked: `build_pyi/` (PyInstaller work dir) and `test-mission/develop` — build
leftovers, not deliverables. Consider `.gitignore`ing `build_pyi/`.

## Scope

| # | Ticket | Status |
|---|--------|--------|
| 01 | Commit the `__main__` entry-point fix + guard it against regression (smoke-test the built exe in CI) | ✅ |
| 02 | Publish the first release so `dcs-bridge-<version>.zip` (with `dcs-serve.exe`) becomes downloadable | ✅ |
| 03 | Document the mandatory `MissionScripting.lua` sanitisation lift (found while writing the release notes — undocumented, and nothing connects without it) | ✅ |

Target version: **1.0.0** (decided by David — first public release, so not a PATCH bump).

## Out of scope

- Loose framework version matching (the real subject behind the `capabilities.py`
  scratch edit): `capabilities` demands exact versions, so a mission running
  `mist 4.5.128-DYNSLOTS-02-VEAF` reports `veaf absent — version mismatch`. Deserves its
  own lot.

## Definition of Done — met

- [x] A freshly built `dcs-serve.exe` starts, listens, and logs — verified by CI, not by
      hand: the release workflow smoke-tests both executables before publishing, and a
      `pytest` guard fails if a spec's frozen script loses its `main()` call.
- [x] A GitHub release exists with `dcs-bridge-1.0.0.zip` containing `dcs-serve.exe`,
      `dcs-client.exe` and `dcs-bridge.lua` — downloaded and extracted to confirm.
- [ ] VMCT's `kit` job picks it up automatically on its next release. **Nothing left to do
      here** — the asset it looks for now exists; this box ticks itself on the next VMCT
      release, in the other repo.

## Beyond the original scope

Writing the release notes exposed a prerequisite that was documented nowhere: the DCS
script sanitisation has to be lifted, or `require("socket")` fails and the bridge never
connects. Added as ticket 03 — without it the release would have been published with its
single mandatory DCS-side step missing, which defeats the purpose of shipping it to
helpers.

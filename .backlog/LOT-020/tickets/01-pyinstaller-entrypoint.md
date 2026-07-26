# 01 — `dcs-serve.exe` exits without starting (missing `__main__` guard)

Status: ✅ done
Type: fix

## Symptom

The packaged `dcs-serve.exe` exits immediately with code 0: nothing listens on
`127.0.0.1:7777` (DCS side) or `0.0.0.0:8080` (HTTP side), and it prints nothing — so a
maker sees a window flash and vanish. `poetry run dcs-serve` works fine, which is why it
went unnoticed.

## Cause

`dcs-serve.spec` passes `src/dcs_bridge/serve/app.py` to `Analysis([...])`, i.e. that
module **is** the frozen script. PyInstaller runs it top-to-bottom: the Typer app `_cli`,
`main()` and `_serve()` get defined, then the process ends — nothing calls `main()`. The
Poetry entry point (`[project.scripts] dcs-serve = "dcs_bridge.serve.app:main"`) is what
normally invokes it, and it does not exist inside the exe.

Note: `dcs-client.spec` bundles `src/dcs_bridge/client/app.py` the same way — **check it
too**, it very likely has the same defect.

## Fix (already applied in the working tree, uncommitted)

```python
if __name__ == "__main__":
    # PyInstaller bundles this file as the script, so it must invoke the entry
    # point itself (the `dcs-serve = ...:main` console-script does it for Poetry).
    main()
```

Verified manually: rebuilt exe logs `TCP server listening on ('127.0.0.1', 7777)` +
`Uvicorn running on http://0.0.0.0:8080`, accepted `DCS connected`, and answered a real
`POST /api/exec` (a `world.getAirbases()` capture) end-to-end.

## Tasks

- [x] Commit the `__main__` guard in `serve/app.py` (⚠️ **only** that file — see the PRD's
      warning about the `capabilities.py` scratch edit that must be reverted).
- [x] Apply the same guard to `client/app.py` if it lacks one, and check `dcs-client.exe`
      actually runs.
- [x] **Regression guard in CI** — a unit test cannot catch this (it is a packaging
      defect). In `.github/workflows/release.yml`, after `pyinstaller`, smoke-test the
      built exe: start `dist/dcs-serve.exe` in the background, poll until TCP 7777
      accepts a connection (fail after ~20 s), then kill it. Cheap, and it would have
      caught this.
- [x] Consider `.gitignore`ing `build_pyi/`.

## Definition of Done

- `dcs-serve.exe` (and `dcs-client.exe`) start correctly when double-clicked.
- CI fails if a future change stops the exe from listening.
- `ruff` / `mypy` / `pytest` green.

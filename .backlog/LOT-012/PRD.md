# Lot LOT-012 — Fix missing `[build-system]` in pyproject.toml

Status: ✅ done

**Effort**: XS
**Branch**: fix/lot-012

## Problem Statement

`pyproject.toml` declares `[tool.poetry]` (name, version, scripts) but has **no
`[build-system]` table**. This means any PEP 517–compliant installer other than the
`poetry` CLI itself — `pip install`, `pipx install`, `pip install git+...` — cannot
determine which build backend to use, falls back to the legacy `setuptools` backend,
and produces a nameless/versionless wheel with **no console-script entry points**.

Confirmed by reproduction (CTLD project, 2026-07-10):

```
pip install "git+https://github.com/VEAF/VEAF-dcs-bridge.git@develop"
# ... "Building wheel for UNKNOWN (pyproject.toml)"
# Successfully installed UNKNOWN-0.0.0
```

`pip show UNKNOWN` confirms empty name/version/metadata, and no `dcs-serve.exe` /
`dcs-client.exe` are created in the venv's `Scripts/` — the `[tool.poetry.scripts]`
entries are silently dropped since the fallback backend does not read Poetry's
metadata format.

This blocks any downstream project (e.g. CTLD's dev-setup tooling) from installing
dcs-bridge via `pip`/`pipx` from Git or, once cut, from PyPI — the released artifact
would have the same problem unless built and published exclusively via `poetry build`
(bypassing the bug at publish time, but leaving `pip install git+...` from source
broken for anyone building from a checkout, and leaving the repo non-compliant with
standard Python packaging expectations).

## Solution

Add the missing declaration:

```toml
[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
```

Verify with a clean-room install (`pip install git+https://github.com/VEAF/VEAF-dcs-bridge.git@develop`
into a fresh venv) that `dcs-serve` and `dcs-client` entry points are created and
`pip show dcs-bridge` reports the correct name/version from `[tool.poetry]`.

## User Stories

1. As a downstream project (e.g. CTLD), I want `pip install git+https://github.com/VEAF/VEAF-dcs-bridge.git@<ref>`
   to produce working `dcs-serve`/`dcs-client` executables, so that I can wire dcs-bridge
   into a project-local venv without depending on `poetry` being installed.
2. As a maintainer, I want `pyproject.toml` to be PEP 517–compliant, so that any
   standard installer (pip, pipx, build, uv) works, not just the `poetry` CLI.

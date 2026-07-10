# Lot LOT-014 — Migrate pyproject.toml metadata to PEP 621 (`[project]`)

Status: ✅ done

**Effort**: S
**Branch**: chore/lot-014

## Problem Statement

`poetry check` emits five deprecation warnings because project metadata is declared
under Poetry's legacy `[tool.poetry]` keys instead of the standard PEP 621 `[project]`
table (supported natively by `poetry-core` since Poetry 2.0):

```
Warning: [tool.poetry.license] is deprecated. Use [project.license] instead.
Warning: [tool.poetry.authors] is deprecated. Use [project.authors] instead.
Warning: [tool.poetry.homepage] is deprecated. Use [project.urls] instead.
Warning: [tool.poetry.repository] is deprecated. Use [project.urls] instead.
Warning: Defining console scripts in [tool.poetry.scripts] is deprecated. Use [project.scripts] instead.
```

These are warnings only — the build works (see LOT-012) — but they clutter every
`poetry check` / `poetry install` run and the repo is not aligned with the current
Poetry / packaging convention. Left alone, they become hard errors in a future Poetry
major.

## Solution

Move the affected fields to a PEP 621 `[project]` table while keeping Poetry-specific
config (dependency groups, package layout) under `[tool.poetry]`:

- `name`, `version`, `description`, `readme`, `license`, `authors` → `[project]`
- `homepage` / `repository` → `[project.urls]`
- `[tool.poetry.scripts]` → `[project.scripts]`
- dependencies: decide between keeping `[tool.poetry.dependencies]` (Poetry-managed,
  simplest) or moving `requires-python` + `dependencies` to `[project]` — evaluate in
  the ticket; the minimal change keeps runtime deps under Poetry.

## Acceptance criteria

- `poetry check` reports no deprecation warnings related to the migrated fields.
- `poetry install`, `poetry build`, and `pip wheel . --no-deps` still produce a wheel
  named `dcs-bridge` at the correct version with both `dcs-serve` / `dcs-client`
  console-script entry points (no regression on LOT-012).
- Quality gate green (ruff, mypy, pytest) and CI green.

## User Stories

1. As a maintainer, I want `pyproject.toml` to use the standard PEP 621 `[project]`
   table, so that `poetry check` is clean and the repo stays compatible with future
   Poetry majors and other PEP 621 tooling.

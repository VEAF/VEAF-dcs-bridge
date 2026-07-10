# 01 — Move metadata and scripts to a PEP 621 `[project]` table

Status: ✅ done
Type: chore

## What to build

Restructure `pyproject.toml` so PEP 621 metadata lives under `[project]`, leaving only
Poetry-specific configuration under `[tool.poetry]`:

- Add a `[project]` table with `name`, `version`, `description`, `readme`,
  `license`, `authors`, and `requires-python`.
- Add `[project.urls]` with `Homepage` and `Repository` (replacing
  `[tool.poetry.homepage]` / `[tool.poetry.repository]`).
- Add `[project.scripts]` with `dcs-serve` / `dcs-client` (replacing
  `[tool.poetry.scripts]`).
- Keep `[tool.poetry]` for `packages` (src layout) and the dependency groups.
- Decide on the dependency block: minimal change keeps `[tool.poetry.dependencies]`
  as-is (Poetry resolves them); only migrate to `[project.dependencies]` if it stays
  compatible with the existing lockfile and groups. Document the choice in the PR.

## Acceptance criteria

- [x] `poetry check` prints no deprecation warnings — reports `All set!`.
- [x] `pip wheel . --no-deps` builds `dcs_bridge-0.6.4-py3-none-any.whl` whose
      `entry_points.txt` still declares both `dcs-serve` and `dcs-client`, with all
      nine `Requires-Dist` deps preserved (LOT-012 regression guard passes).
- [x] `poetry lock` / `poetry install` succeed; deps kept Poetry-managed via
      `dynamic = ["dependencies"]` (minimal change — caret constraints untouched).
- [x] Quality gate green (`ruff`, `mypy`, `pytest`). CI: to confirm on PR.

## Blocked by

None — independent of LOT-012 (already merged) and LOT-013.

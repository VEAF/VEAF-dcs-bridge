# 01 — Add `[build-system]` to pyproject.toml

Status: ✅ done
Type: fix

## What to build

Add to `pyproject.toml`:

```toml
[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
```

Placement: near the top, before `[tool.poetry]` (conventional position, not load-bearing).

## Acceptance criteria

- [x] `[build-system]` present with `poetry-core` backend.
- [x] Clean-room repro passes: `pip wheel . --no-deps` from the checkout builds
      `dcs_bridge-0.6.2-py3-none-any.whl` (named + versioned, no longer `UNKNOWN-0.0.0`),
      and its `entry_points.txt` declares both `dcs-serve` and `dcs-client` console
      scripts.
- [x] `poetry install` / `poetry check` still work unchanged (no regression for the
      existing dev workflow).
- [x] `pyproject.toml` still passes any existing lint/format check — CI green on PR #15.

## Blocked by

None — can start immediately.

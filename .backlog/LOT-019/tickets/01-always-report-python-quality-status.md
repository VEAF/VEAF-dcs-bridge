# 01 — Always report the `python-quality` required status

Status: ⬜ ready
Type: fix

## What to build

Rework `.github/workflows/python-quality.yml` so the required check always reports:

- Remove the workflow-level `paths:` filter (job runs on every PR / relevant push).
- Detect whether Python-relevant paths changed (`dorny/paths-filter` or a `git diff`
  against the base), and **only then** run ruff / mypy / pytest.
- When nothing relevant changed, the job **skips the heavy steps and ends green**, so the
  required `python-quality` context is present and successful.

Keep the same job/check name (`python-quality`) so the existing branch-protection rule
matches without reconfiguration.

## Acceptance criteria

- [ ] A doc-only / backlog-only PR shows a green `python-quality` check and is mergeable
      with no admin override.
- [ ] A PR touching `src/**` / `test/**` / `pyproject.toml` still runs the full gate
      (ruff, mypy, pytest) and fails on violations.
- [ ] Verified on a throwaway doc-only PR before closing.

## Blocked by

None.

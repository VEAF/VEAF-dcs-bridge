# Lot LOT-019 — Doc-only PRs are blocked by the required `python-quality` check

Status: ✅ done

**Effort**: S
**Branch**: fix/LOT-019 (merged)

## Problem Statement

`python-quality.yml` is gated by a `paths` filter (`src/**`, `test/**`, `pyproject.toml`,
the workflow file). A PR that touches only `docs/**` or `.backlog/**` therefore **never
triggers** the workflow. Because `python-quality` is a **required** status check in the
branch-protection rules, its absence leaves the PR permanently `BLOCKED` — a required
check that will never report.

Hit on 2026-07-11 with PR #20 (ADR-0005, doc-only): CI was green (Sourcery passed) yet the
PR could not be merged and required an admin override. This recurs on **every** doc-only
or backlog-only PR.

## Solution

Make `python-quality` always produce its required status, reporting success when there is
no Python code to check. Preferred pattern (GitHub required-check + paths-filter):

- Drop the workflow-level `paths` filter so the job **always runs** on PRs, and gate the
  actual work (ruff/mypy/pytest) internally — e.g. a `dorny/paths-filter` step (or a small
  `git diff` check) that skips the heavy steps when no `src/**`/`test/**`/`pyproject.toml`
  changed, the job still ending green.

Alternative considered: remove `python-quality` from the required checks — rejected, it
would drop enforcement on code PRs.

## User Stories

1. As a maintainer opening a doc-only or backlog-only PR, I want it to be mergeable when
   CI is green, without an admin override.

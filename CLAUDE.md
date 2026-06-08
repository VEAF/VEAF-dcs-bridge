# dcs-bridge — Claude Code Instructions

> Generic bridge between DCS World and external consumers (TUI, WebUI, AI agents).

---

## 1. Language and Communication

- **Communication**: Automatically adapt to the language used by the user in their messages.
- **Code & Documentation**: Exclusively use English for functions, variables, comments, docstrings, commit messages, PR descriptions, and all technical project documentation.

---

## 2. AI Behavior (Surgical Mode)

- **RULE N°1 (Surgical Changes)**: NEVER modify adjacent code, comments, or formatting that are not directly related to the request. Do not refactor functional code.
- **RULE N°2 (Absolute Simplicity)**: Produce the minimum volume of code necessary to solve the current problem. Do not add any speculative features or abstractions.
- **RULE N°3 (Zero Assumptions)**: If an instruction is ambiguous, contradictory, or confusing, STOP immediately and ask questions to clarify the intent.

---

## 3. Code Quality and Style (Zero Tolerance)

- **IDE Errors**: No warnings or errors must remain in the editor (Pylance, mypy, ruff).
- **Static Typing**: Type annotations are mandatory for all functions with explicit return syntax `-> ReturnType`. Use modern unions like `Type | None`.
- **Docstrings**: Write comprehensive docstrings strictly following the Google format (with `Args:`, `Returns:`, `Raises:` sections).

---

## 4. TDD and Behavioral Coverage Rule

- **TDD Cycle**: Always write a failing unit test before implementing any business logic, make the test pass, then refactor.
- **COVERAGE RULE (Zero Regression)**:
  - *New Code*: Every new function, method, or class must be delivered with its corresponding unit tests. Code is considered incomplete without its tests.
  - *Existing Code*: Any modification to existing business logic requires updating existing tests or creating a new test if it is missing.

---

## 5. Git Flow and Commits

- **Branch Management**: All work must be done on feature branches (`feature/*` or `fix/*`) created from `develop`. Never commit directly to `main`.
- **Commit Messages**: Scrupulously respect the Conventional Commits specification in English (`type(scope): description`).

---

## 6. Backlog and Changelog Maintenance

- **Real-Time Updates**: `BACKLOG.md` must exactly reflect the progress status of tasks.
- **Archiving**: Move closed tickets completed for more than 3 days from `BACKLOG.md` to `backlog-archive.md`.

---

## 7. Semantic Routing Rules

### Python (`src/dcs_bridge/` or `test/`)

- **Architecture**: Respect the `serve/`, `client/`, and `common/` module structure.
- **Environment Management**: Dependencies are managed via Poetry. Activate the virtual environment using `poetry shell`.
- **Logging**: Use the standard `logging` module with structured output. No bare `print()` calls.
- **Quality Validation**: Run `poetry run ruff check src/ --fix` and `poetry run mypy src/`. Resolve errors rather than adding exclusions.
- **Tests**: Run `poetry run pytest`. Test files match `test_*.py` and live in `test/`.

### Lua (`src/lua/`)

- **Environment**: Pure Lua 5.1 executing inside DCS World. No external dependencies.
- **Naming Conventions**: Module table in camelCase (`dcsBridge = {}`).
- **Socket**: Always non-blocking (`settimeout(0.0001)`). Never block the simulation thread.

---

## 8. Default Action Workflow (apply automatically unless told otherwise)

For every action requested by the user, execute these steps in order:

1. **Analyze** the request and identify the impacted files and scope.
   - If the request is exploratory (question, analysis, no code change), stop here.
2. **Create a lot** in `BACKLOG.md`: add a new lot with a unique ID, description, tickets, estimated effort, and status `⬜`. Add it to the Summary table.
3. **Create a branch** from `develop` following the naming convention (`feature/<id>` or `fix/<id>`).
4. **Implement** the change: code + unit tests (TDD rules apply).
5. **Run tests**: `poetry run pytest`. Fix any failure before continuing.
6. **Run quality gate**: `poetry run ruff check src/ --fix && poetry run mypy src/`. Resolve all errors before continuing.
7. **Update `CHANGELOG.md`** under `[Unreleased]` with one clear entry.
8. **If the user needs to test manually**: stop and wait for explicit approval before continuing. Otherwise, proceed directly.
9. **Commit** all changes (Conventional Commits format in English) and **push** the branch.
10. **Open a PR** targeting `develop` and report the PR URL to the user.
11. **Monitor the PR**: wait for CI. Address any feedback, then merge when approved.
12. **After merge**: switch back to `develop`, pull, and confirm to the user.

---

## 9. Single Change Checklist (detail of step 4–7 above)

1. Make code changes and write associated unit tests according to TDD rules.
2. Run all quality validation tools (`ruff`, `mypy`, `pytest`).
3. Update `CHANGELOG.md` under the `[Unreleased]` section.
4. Increment the PATCH version in `pyproject.toml`.
5. Run `poetry install` to update the development environment.

---

## 10. Pull Request Process

After pushing a branch and creating a PR:
- **Do NOT request a Copilot review.** Sourcery reviews PRs automatically.
- Request a review only if Sourcery posts a comment stating it cannot review the PR.

After a PR is merged:
- **Always** switch to `develop`, run `git pull`, and confirm the merge commit is present before doing any further work.

---

## 11. Pipeline Commands

- **Quality gate**: `poetry run ruff check src/ && poetry run mypy src/ && poetry run pytest`
- **Release**: use the `/release-notes` slash command

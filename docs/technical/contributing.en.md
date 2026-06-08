# Contributing

## Development prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/) ≥ 1.8
- Git

## Setting up the environment

```bash
git clone https://github.com/VEAF/dcs-bridge.git
cd dcs-bridge
poetry install --with dev
```

## TDD — development cycle

dcs-bridge enforces strict TDD:

1. **Red** — write a failing test for the target feature
2. **Green** — implement the minimum code to pass the test
3. **Refactor** — improve the code without breaking tests

All new code must be delivered with unit tests. Code without tests is considered incomplete.

## Quality commands

```bash
# Lint + autofix
poetry run ruff check src/ --fix

# Type checking
poetry run mypy src/

# Tests
poetry run pytest

# All in one (CI pipeline)
poetry run ruff check src/ --fix && poetry run mypy src/ && poetry run pytest
```

## Commit conventions

dcs-bridge uses [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): short description in English

Optional body explaining the why.
```

**Accepted types:**

| Type | Usage |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `test` | Adding or modifying tests |
| `refactor` | Refactoring without behaviour change |
| `chore` | Maintenance tasks (CI, deps, config) |
| `perf` | Performance improvement |

**Examples:**

```
feat(serve): add /api/health endpoint
fix(lua): prevent nil dereference on empty unit list
docs(readme): add architecture diagram
test(serve): cover CommandBus timeout path
```

## Git Flow

```
master  ──────────────────────────────── (releases)
           ↑ PR merge
develop ─────────────────────────────── (integration)
           ↑ PR merge
feature/lot-NNN  or  fix/lot-NNN
```

- Create branches from `develop`
- Name branches `feature/<id>` or `fix/<id>`
- Never commit directly to `develop` or `master`
- Open a PR targeting `develop`; the team merges after Sourcery review

## Test structure

```
test/
├── test_common_models.py    # Pydantic models, enums
├── test_serve_core.py       # TcpHandler, Snapshot, CommandBus
├── test_serve_api.py        # FastAPI routes (httpx AsyncClient)
├── test_serve_config.py     # ServeConfig
├── test_client_config.py    # ClientConfig
├── test_client_tui.py       # Textual TUI
├── test_mcp_server.py       # MCP tools
└── test_web_server.py       # Web server
```

Shared fixtures are defined within each test file (no global `conftest.py`).

## Adding a dependency

```bash
# Runtime dependency
poetry add package-name

# Development dependency
poetry add --group dev package-name

# Documentation dependency
poetry add --group docs package-name
```

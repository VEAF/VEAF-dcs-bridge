# Contribuer

## Prérequis de développement

- Python 3.11+
- [Poetry](https://python-poetry.org/) ≥ 1.8
- Git

## Installation de l'environnement

```bash
git clone https://github.com/VEAF/dcs-bridge.git
cd dcs-bridge
poetry install --with dev
```

## TDD — cycle de développement

dcs-bridge applique le TDD strict :

1. **Red** — écrire un test qui échoue pour la fonctionnalité visée
2. **Green** — implémenter le minimum de code pour faire passer le test
3. **Refactor** — améliorer le code sans casser les tests

Tout nouveau code doit être livré avec ses tests unitaires. Un code sans test est considéré incomplet.

## Commandes de qualité

```bash
# Lint + autofix
poetry run ruff check src/ --fix

# Vérification de types
poetry run mypy src/

# Tests
poetry run pytest

# Tout en une commande (pipeline CI)
poetry run ruff check src/ --fix && poetry run mypy src/ && poetry run pytest
```

## Conventions de commit

dcs-bridge utilise [Conventional Commits](https://www.conventionalcommits.org/) :

```
type(scope): description courte en anglais

Corps optionnel expliquant le pourquoi.
```

**Types acceptés :**

| Type | Usage |
|---|---|
| `feat` | Nouvelle fonctionnalité |
| `fix` | Correction de bug |
| `docs` | Documentation uniquement |
| `test` | Ajout ou modification de tests |
| `refactor` | Refactorisation sans changement de comportement |
| `chore` | Tâches de maintenance (CI, deps, config) |
| `perf` | Amélioration de performance |

**Exemples :**

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
develop ─────────────────────────────── (intégration)
           ↑ PR merge
feature/lot-NNN  ou  fix/lot-NNN
```

- Créer les branches depuis `develop`
- Nommer les branches `feature/<id>` ou `fix/<id>`
- Ne jamais committer directement sur `develop` ou `master`
- Ouvrir une PR vers `develop` ; l'équipe merge après revue Sourcery

## Structure des tests

```
test/
├── test_common_models.py    # Modèles Pydantic, enums
├── test_serve_core.py       # TcpHandler, Snapshot, CommandBus
├── test_serve_api.py        # Routes FastAPI (httpx AsyncClient)
├── test_serve_config.py     # ServeConfig
├── test_client_config.py    # ClientConfig
├── test_client_tui.py       # Textual TUI
├── test_mcp_server.py       # Outils MCP
└── test_web_server.py       # Serveur web
```

Les fixtures partagées sont définies dans chaque fichier de test (pas de `conftest.py` global).

## Ajouter une dépendance

```bash
# Dépendance runtime
poetry add nom-du-package

# Dépendance de développement
poetry add --group dev nom-du-package

# Dépendance de documentation
poetry add --group docs nom-du-package
```

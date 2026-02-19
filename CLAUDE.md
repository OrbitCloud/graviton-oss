# Graviton CDK

Graviton is a **Python Infrastructure-as-Code development kit** for Azure, built on **Pulumi** with a **Polylith** monorepo architecture. It provides modular, composable building blocks for Azure infrastructure.

## Architecture

**Polylith monorepo** with namespace `orbitcloud_graviton`:

- `components/` — Azure service wrappers (e.g., `az_storage`, `az_postgres`, `az_network`). Each component encapsulates a single Azure resource or tightly coupled set of resources.
- `bases/` — Domain-level abstractions that compose components (e.g., `landing_zone`, `app_workload`, `azure_environment`).
- `test/` — Mirrors the `bases/` and `components/` directory structure.
- `templates/` — Copier templates for scaffolding new components and bases.

## Tech Stack

- **Python** 3.12+ (3.13.3 in `.python-version`)
- **Pulumi** 3.138+ with `pulumi-azure-native`
- **Pydantic** v2 for configuration and validation
- **uv** for dependency management, virtualenvs, and Python version management

## Development Commands

```bash
make fmt        # Ruff autofix + format
make lint       # Ruff check (no fix)
make test       # pytest with coverage
make pyright    # Type checking
make component  # Scaffold a new component
make base       # Scaffold a new base
```

Always run `make fmt` before committing. The full validation chain is:

```bash
make fmt && make lint && make test
```

## Code Standards

- **Formatter/Linter**: Ruff — line length 100, rules: B, C4, E, F, I, UP, W, ARG001
- **Type checker**: Pyright in basic mode
- **Imports**: isort via Ruff. First-party: `orbitcloud_graviton`. Third-party: `pulumi`, `pulumi_azure_native`, `pulumi_azuread`, `pydantic`
- **Testing**: pytest with `pytest-cov`. Test files: `test.py`, `test_*.py`, `tests.py`
- **Pre-commit hooks**: commitizen (commit message validation), ruff, pyright, standard file checks

## Commit Messages

**Conventional Commits** enforced by commitizen:

```
feat(ComponentName): Add new capability
fix(ComponentName): Correct behavior description
refactor(ComponentName): What was restructured
chore(python-deps): Update packages
style: Ruff post-update fixes
```

- `feat:` triggers minor version bump
- `fix:` triggers patch version bump
- Scope is typically the component/base class name in PascalCase
- Version is managed by commitizen — never edit `VERSION` or version in `pyproject.toml` manually

## Patterns

- Azure resource classes wrap Pulumi resources with opinionated defaults
- Pydantic v2 models with `ConfigDict` for configuration validation
- Type hints everywhere — use `|` union syntax (Python 3.10+)
- `enum.StrEnum` for constrained string values
- Components expose a primary class that takes Pydantic config and creates Pulumi resources

## CI/CD

GitHub Actions pipeline (`.github/workflows/build.yml`):
1. Run `make lint` and `make test` on all PRs and pushes
2. Smoke test: build wheel, install in isolated env, verify imports
3. On main: commitizen creates bump commits, changelog updates, and GitHub releases

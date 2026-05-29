# Graviton CDK

Infrastructure-as-Code library for Azure, built on Pulumi with a Polylith monorepo architecture.

## Architecture

- **Monorepo layout**: Polylith pattern
  - `components/` -- Azure service wrappers (e.g., container_app, postgres, firewall)
  - `bases/` -- Domain abstractions composed from components
  - `test/` -- pytest tests mirroring the source tree
- **Namespace**: `orbitcloud_graviton`

## Build and Test

```bash
make fmt      # Ruff autofix + format
make lint     # Ruff check (no fix)
make test     # pytest with coverage
make pyright  # Type checking
```

Run validation before committing: `make fmt && make lint && make test`

## Key Patterns

- **Pulumi** for resource provisioning -- components wrap Pulumi resources with opinionated defaults
- **Pydantic v2** models with `ConfigDict` for configuration and input validation
- **pytest** with Pulumi mocking via `test/conftest.py` fixtures
- **Python 3.10+** type hints (union syntax `X | None`, `enum.StrEnum`)

## Workflow

- PR links are automatically surfaced after `git push` via a PostToolUse hook
- Use `make` targets for all build, lint, and test operations
- Follow TDD: write a failing test, implement, refactor

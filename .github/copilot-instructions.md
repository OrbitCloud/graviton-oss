# Graviton CDK - Repository Context

Graviton CDK is a **Pulumi-based Infrastructure-as-Code library for Azure**, organized as a
**Polylith monorepo**. It provides opinionated, reusable components that wrap Azure resources with
sensible defaults.

## Directory Structure

| Directory       | Purpose                                                        |
|-----------------|----------------------------------------------------------------|
| `components/`   | Azure service wrappers (one component per Azure service)      |
| `bases/`        | Domain abstractions shared across components                   |
| `test/`         | pytest test suite; paths mirror source paths                   |
| `docs/`         | Requirements, ADRs, and documentation                          |
| `.claude/`      | **Source-of-truth** agent and command definitions (see below)  |
| `.github/agents/`| Copilot-compatible agents derived from `.claude/agents/`      |

## Namespace

All Python packages live under the `orbitcloud_graviton` namespace.

## Toolchain and Validation

Run the full validation sequence after any code change:

```bash
make fmt          # Ruff autofix + formatting
make lint         # Ruff check (no autofix)
make test         # pytest with coverage
make pyright      # Type checking (run when touching type signatures)
```

The combined command `make fmt && make lint && make test` is the standard CI gate.

## Coding Conventions

- **Python 3.10+** with modern union syntax (`X | None`, not `Optional[X]`)
- **Pydantic v2** models with `ConfigDict` for all configuration objects
- **`enum.StrEnum`** for constrained string values
- **Type hints** on all public functions and class attributes
- **Ruff** for linting and formatting; line length is **100**
- Azure resource classes wrap Pulumi resources with opinionated defaults
- Components expose a primary class that takes a Pydantic config and creates Pulumi resources

## Testing

- **pytest** is the test framework
- Pulumi resource mocking is provided via fixtures in `test/conftest.py`
- Test file paths mirror source paths (e.g., `components/foo/` -> `test/components/foo/`)
- Always write tests before implementation (TDD: red, green, refactor)

## Requirements and Workflow

Feature requirements live in `docs/requirements/[feature]/README.md`. The development workflow
follows a dev-then-review cycle:

1. A **developer agent** implements in TDD increments, tracking progress in task files
2. A **reviewer agent** critiques the branch changes and writes a review file
3. The cycle repeats until the reviewer approves

The full cycle is defined in `.claude/commands/dev-cycle.md`. Agent role definitions live in
`.claude/agents/dev.md` and `.claude/agents/reviewer.md` -- these are the authoritative source.
The `.github/agents/` files are derived copies adapted for Copilot frontmatter.

## Key Patterns

- Pydantic v2 `ConfigDict` for resource configuration
- `enum.StrEnum` for Azure SKU tiers, replication types, etc.
- Pulumi `Output` transformations handled via `.apply()` only when necessary
- Resource naming follows project conventions established in existing components
- SOLID principles, especially single responsibility per component

# uv Migration Requirements

## Overview

Replace Poetry with [uv](https://docs.astral.sh/uv/) as the package manager, dependency resolver, and Python version manager across local development and CI/CD. Poetry is removed entirely.

## Goals

- **Primary**: Significantly faster `install` / `sync` cycles (uv is 10–100x faster than Poetry)
- **Secondary**: Simplify the toolchain — uv replaces Poetry, pip, virtualenv, and pyenv in one binary
- **Tertiary**: Modernise `pyproject.toml` to PEP 621 (`[project]`) and PEP 735 (`[dependency-groups]`) standards

## User Stories

- As a developer, I want `make install` to finish in seconds so I can start working quickly.
- As a developer, I want a single tool (`uv`) to manage Python versions, virtualenvs, and packages.
- As a CI engineer, I want the GitHub Actions pipeline to use `uv` so that builds are faster and the workflow is simpler.
- As a downstream consumer, I want to install `orbitcloud-graviton` via `uv add` and import any component or base without surprises.

## Functional Requirements

### Must Have (P0)

- [ ] `pyproject.toml` migrated from `[tool.poetry.*]` to `[project]` (PEP 621) with all runtime dependencies
- [ ] Dev dependencies migrated to `[dependency-groups]` (PEP 735, native uv support)
- [ ] Build backend switched from `poetry-core` to a backend that correctly handles the Polylith namespace package split (see Namespace Package Integrity section)
- [ ] All 33+ sub-packages from `components/` and `bases/` are included in the built wheel under the `orbitcloud_graviton` namespace
- [ ] The built wheel installs cleanly in a fresh downstream virtualenv with no missing packages
- [ ] Every component and base is importable after install (e.g. `from orbitcloud_graviton.az_storage import ...`, `from orbitcloud_graviton.landing_zone import ...`)
- [ ] `uv.lock` generated and committed; `poetry.lock` deleted
- [ ] `poetry.toml` deleted (venv config moves to uv defaults)
- [ ] `Makefile` updated: all `poetry run <cmd>` → `uv run <cmd>`, `poetry install` → `uv sync`
- [ ] `make install-poly` target removed (Polylith plugin dropped)
- [ ] `make outdated` / `make update` targets updated to use `uv` equivalents
- [ ] GitHub Actions `test` job updated: replace Poetry install steps with `astral-sh/setup-uv` + `uv sync`
- [ ] Python version pinned via `.python-version` file (created by `uv python pin 3.13.3`), readable by both uv and mise/asdf
- [ ] `CLAUDE.md` updated to reflect new commands

### Should Have (P1)

- [ ] `commitizen` version provider updated to `pep621` so version is managed in `[project].version` instead of `[tool.commitizen].version`
- [ ] `setup-python` step in CI replaced with uv's built-in Python management (remove `actions/setup-python` dependency)
- [ ] uv caching configured in CI via `astral-sh/setup-uv` built-in cache (`enable-cache: true`)

### Nice to Have (P2)

- [ ] `uv.toml` created for project-level uv config if needed
- [ ] `.tool-versions` updated or replaced with `.python-version`

## Non-Functional Requirements

- **Performance**: `uv sync` on a warm cache must be faster than `poetry install` on a warm cache
- **Backwards Compatibility**: No change to public API or package structure; only tooling changes
- **Lockfile hygiene**: `uv.lock` committed and kept up-to-date (equivalent role to `poetry.lock`)
- **CI parity**: The same lint + test commands run in CI as locally

## Key Technical Changes

### `pyproject.toml` restructure

| Before | After |
|--------|-------|
| `[tool.poetry]` + `[tool.poetry.dependencies]` | `[project]` with `dependencies = [...]` |
| `[tool.poetry.group.dev.dependencies]` | `[dependency-groups]` `dev = [...]` |
| `build-backend = "poetry.core.masonry.api"` | `build-backend = "hatchling.build"` |
| `packages = [{include, from}]` | `[tool.hatch.build.targets.wheel].sources` |

### Namespace Package Integrity

This is the highest-risk part of the migration and must be explicitly validated.

**Current structure**: `orbitcloud_graviton` is a PEP 420 implicit namespace package split across two source roots with no top-level `__init__.py` in either `components/orbitcloud_graviton/` or `bases/orbitcloud_graviton/`. All 33+ sub-packages have their own `__init__.py`.

**Problem**: The new build backend must correctly:
1. Discover packages across both source roots (`bases/` and `components/`)
2. Merge them under a single `orbitcloud_graviton` namespace in the wheel
3. Not inject a synthetic `__init__.py` at the namespace level (which would break the namespace package mechanism for downstream users who extend the namespace)

**Candidate approaches** (to be validated during implementation):

| Approach | Risk |
|----------|------|
| hatchling `sources = ["bases", "components"]` + `include-namespace-packages = true` | Low if hatchling supports it; needs verification |
| hatchling with explicit `packages` list | Verbose but predictable; mirrors current Poetry config |
| setuptools with `find_namespace_packages(where=["bases", "components"])` | Well-proven for namespace splits; more config required |

The implementation must choose and validate one approach by running the smoke test (see Acceptance Criteria).

### Makefile

| Before | After |
|--------|-------|
| `poetry install` | `uv sync` |
| `poetry run pytest ...` | `uv run pytest ...` |
| `poetry run ruff ...` | `uv run ruff ...` |
| `poetry run pyright ...` | `uv run pyright ...` |
| `poetry show --outdated` | `uv tree --outdated` |
| `poetry update` | `uv lock --upgrade` |
| `poetry self add ...` | *(removed — no plugin system)* |

### GitHub Actions

Replace the Poetry-based setup (snok/install-poetry + manual venv caching) with:

```yaml
- uses: astral-sh/setup-uv@v5
  with:
    enable-cache: true
- run: uv sync
- run: uv run make lint
- run: uv run make test
```

### Downstream installability smoke test

A script or CI step must verify the built wheel works in an isolated environment:

```bash
# Build the wheel
uv build

# Install into a fresh venv and test imports
uv run --isolated --with dist/orbitcloud_graviton-*.whl python - <<'EOF'
# Spot-check one component and one base
from orbitcloud_graviton.az_storage import StorageAccount
from orbitcloud_graviton.az_network import VirtualNetwork
from orbitcloud_graviton.landing_zone import LandingZone
from orbitcloud_graviton.app_workload import AppWorkload
print("All imports OK")
EOF
```

This test must pass in CI on every PR as part of the `test` job.

## Affected Files

| File | Change |
|------|--------|
| `pyproject.toml` | Full restructure (see above) |
| `poetry.lock` | Deleted |
| `poetry.toml` | Deleted |
| `uv.lock` | Created (committed) |
| `.python-version` | Created (`uv python pin 3.13.3`) |
| `Makefile` | All `poetry` references replaced; unused `pulumi package gen-sdk` call removed from `install` target |
| `.github/workflows/build.yml` | Poetry steps replaced with uv |
| `CLAUDE.md` | Dev commands updated |

## Out of Scope

- Changes to any component or base source code
- Changes to Pulumi resource logic
- Migrating from Polylith monorepo architecture
- Publishing to PyPI (current GitHub Releases workflow unchanged)
- Removing `polylith` CLI tooling itself (only the Poetry plugin is removed)

## Dependencies

- `uv` >= 0.5 (for PEP 735 `[dependency-groups]` support)
- `hatchling` (added as build-system dependency)
- `astral-sh/setup-uv@v5` GitHub Action

## Open Questions

- [ ] **Build backend choice**: Does hatchling's `sources` + `include-namespace-packages` correctly handle the implicit namespace split, or do we need setuptools `find_namespace_packages`? Must be verified with a `uv build` + install smoke test before committing to an approach.
- [ ] **Namespace `__init__.py`**: Does the chosen build backend inject a synthetic `__init__.py` at `orbitcloud_graviton/`? If so, it must be suppressed — a synthetic `__init__.py` would break downstream projects that also extend the `orbitcloud_graviton` namespace.
- [ ] Does the `commitizen-action` in CI work correctly when the version is in `[project].version` (pep621 provider)? Needs verification before the release job is touched.
- [ ] Does `copier` work correctly when invoked via `uv run copier`? It's a dev dependency so should be fine — confirm during implementation.
- [ ] Should `.tool-versions` be kept alongside `.python-version` for developers still using asdf/mise, or removed entirely?

## Acceptance Criteria

- [ ] `uv sync` installs all dependencies cleanly from scratch (no `poetry` required on the machine)
- [ ] `make fmt && make lint && make test` all pass after migration
- [ ] `make pyright` passes
- [ ] `uv build` produces a `.whl` and `.tar.gz` with all 33+ sub-packages present under `orbitcloud_graviton`
- [ ] The wheel installs in a clean venv and the import smoke test passes for at least one component and one base
- [ ] The installed wheel contains no `orbitcloud_graviton/__init__.py` (namespace package must remain implicit)
- [ ] GitHub Actions `test` job passes on a PR, including the smoke test step
- [ ] GitHub Actions `release` job (commitizen bump) still creates correct version tags
- [ ] `poetry.lock` is gone; `uv.lock` is committed and resolves deterministically
- [ ] No Poetry executable is needed anywhere in the dev or CI workflow

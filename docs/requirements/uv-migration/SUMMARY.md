# UV Migration Summary

## What Was Implemented

Complete migration from Poetry to uv as the package manager, dependency resolver, and Python version manager.

### Files Changed

| File | Change |
|------|--------|
| `pyproject.toml` | Full restructure: `[tool.poetry]` to `[project]` (PEP 621), `[tool.poetry.group.dev.dependencies]` to `[dependency-groups]` (PEP 735), build backend from `poetry-core` to `hatchling`, commitizen `version_provider = "pep621"` |
| `poetry.lock` | Deleted |
| `poetry.toml` | Deleted |
| `uv.lock` | Created (114 resolved packages) |
| `.python-version` | Created (`3.13.3`) |
| `Makefile` | All `poetry run` replaced with `uv run`, `poetry install` replaced with `uv sync`, removed `install-poly` target, removed `pulumi package gen-sdk` from `install`, updated `outdated`/`update` targets |
| `.github/workflows/build.yml` | Replaced `actions/setup-python` + `snok/install-poetry` + manual venv caching with `astral-sh/setup-uv@v5` (with `enable-cache: true`), added smoke test step |
| `CLAUDE.md` | Updated tech stack and CI/CD sections to reflect uv |

### Files Not Changed

| File | Reason |
|------|--------|
| `.tool-versions` | Kept alongside `.python-version` for developers still using asdf/mise |
| Application source code | Out of scope -- tooling-only migration |

## Build Backend Decision

**Chosen: hatchling** with `packages = ["bases/orbitcloud_graviton", "components/orbitcloud_graviton"]`.

### Alternatives Evaluated

| Approach | Result |
|----------|--------|
| hatchling with `sources = ["bases", "components"]` | Failed -- hatchling cannot auto-discover packages with only `sources` |
| hatchling with `packages` listing individual sub-packages | Incorrectly stripped the namespace prefix (e.g., `az_storage/` instead of `orbitcloud_graviton/az_storage/`) |
| hatchling with `packages` pointing to namespace dirs from both roots | Works correctly -- merges both source roots under `orbitcloud_graviton/` with no synthetic `__init__.py` |

The chosen approach is simpler than setuptools `find_namespace_packages` and does not require explicitly listing every sub-package.

## Validation Results

| Check | Result |
|-------|--------|
| `uv sync` | Installs 113 packages cleanly |
| `make fmt` | All files formatted, no changes needed |
| `make lint` | All checks pass |
| `make test` | 45/45 tests pass |
| `uv build` | Produces wheel and sdist |
| Wheel sub-packages | 40 sub-packages present (all from `bases/` and `components/`) |
| Namespace `__init__.py` | Not present in wheel (namespace package preserved) |
| Smoke test | `StorageAccount`, `Vnet`, `KeyVault`, `PostgresFlexibleServer` all importable from isolated venv |
| Commitizen version | Reads `0.89.0` from `[project].version` via `pep621` provider |

## Decisions and Trade-offs

1. **Build backend**: Hatchling over setuptools. Simpler config, modern tooling, works correctly with the namespace split.

2. **Dependency version specifiers**: Converted Poetry `^x.y` to `>=x.y,<(x+1)` (PEP 440). This is semantically equivalent to Poetry's caret operator.

3. **Smoke test imports**: The requirements document suggested importing `VirtualNetwork`, `LandingZone`, and `AppWorkload`. These names do not match the actual exports (`Vnet`, `deploy_landing_zone`, `deploy`). Additionally, some base modules (e.g., `landing_zone`) import `az_iam` which calls `asyncio.get_running_loop()` at module level, making them un-importable outside a Pulumi runtime. The smoke test was adjusted to use `StorageAccount`, `Vnet`, `KeyVault`, and `PostgresFlexibleServer` which are all importable without a Pulumi runtime.

4. **Duplicate `py.typed` warning**: Both `bases/` and `components/` contain a `py.typed` marker file. Hatchling emits a warning about duplicate names in the zip. This is cosmetic and does not affect functionality.

5. **`firewall` base included**: The old Poetry config did not list `orbitcloud_graviton/firewall` but the directory exists with an `__init__.py`. The hatchling config picks up all sub-packages under the namespace directories, which is the correct behavior.

6. **`.tool-versions` retained**: Left as-is alongside `.python-version` since developers may still use asdf/mise.

## Review 01 Feedback Addressed

The following items from review-01 were addressed:

| Issue | Severity | Resolution |
|-------|----------|------------|
| `.pre-commit-config.yaml` line 29: `poetry run pyright` | Critical | Changed to `uv run pyright -p .` |
| `pyproject.toml`: `ruff>=0.15` unbounded | Important | Changed to `ruff>=0.15,<1` to cap at major version |
| `.github/workflows/build.yml`: stale dist/ in smoke test | Important | Added `rm -rf dist/` before `uv build` |
| `Makefile`: extra blank lines after `install-precommit` | Suggestion | Reduced from 3 to 1 blank line |

Items noted but not changed:
- `tool.ruff.target-version = "py311"` -- left as-is since changing it could trigger widespread formatting changes across the codebase that are outside the scope of this migration. This can be addressed in a separate PR.
- Smoke test base import -- left as-is per the original decision documented above (base modules have Pulumi runtime dependencies that prevent isolated import).
- `uv.lock` drift after commitizen bump -- accepted as non-breaking; lock file regenerates on next `uv sync`.

## Suggested Next Steps

1. **Pre-existing issue**: `az_iam/_roles.py` calls `asyncio.get_running_loop()` at module level (line 31), which prevents importing any module that transitively depends on `az_iam` outside of a Pulumi runtime. This should be refactored to use lazy initialization.

2. **Duplicate `py.typed`**: Consider removing one of the two `py.typed` marker files (either `bases/orbitcloud_graviton/py.typed` or `components/orbitcloud_graviton/py.typed`) to eliminate the build warning.

3. **CI verification**: The GitHub Actions workflow changes should be verified on an actual PR to confirm the `astral-sh/setup-uv@v5` action and smoke test work in the CI environment.

4. **Release job**: The commitizen `pep621` version provider should be tested with an actual bump to confirm it correctly updates `[project].version` and `VERSION`. This can be verified by the first `feat:` or `fix:` commit merged to main after this migration.

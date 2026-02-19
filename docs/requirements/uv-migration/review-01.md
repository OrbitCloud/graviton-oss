# Review 01

> Status: addressed
> Date: 2026-02-19
> Reviewer: Code Review Agent
> Verdict: REQUEST CHANGES

## Previous Review Status

No previous reviews.

## New Findings

### Critical (Must Fix)

- **[.pre-commit-config.yaml:29]** The pyright pre-commit hook still uses `poetry run pyright -p .`. This will fail for any developer who has migrated to uv, since Poetry will not be installed. Change to `uv run pyright -p .` to match the Makefile convention.

  ```yaml
  # Current (broken)
  entry: poetry run pyright -p .

  # Fix
  entry: uv run pyright -p .
  ```

### Important (Should Fix)

- **[pyproject.toml:41]** The `ruff` dependency has no upper bound: `ruff>=0.15`. The old Poetry constraint `^0.15` was equivalent to `>=0.15.0, <0.16.0`. Ruff is a pre-1.0 tool that can introduce breaking formatting and lint changes across minor versions. An unbounded constraint means `uv lock --upgrade` could pull in a future ruff version that reformats the entire codebase or flags new lint errors, breaking CI unexpectedly. Consider adding an upper bound:

  ```toml
  "ruff>=0.15,<0.16",
  ```

- **[.github/workflows/build.yml:29]** The smoke test uses a glob in `--with dist/orbitcloud_graviton-*.whl`. If `uv build` produces both `.whl` and `.tar.gz` (it does by default), the glob is fine since it only matches `.whl`. However, if a previous build left stale wheels in `dist/`, the glob could match multiple files. Consider adding `rm -rf dist/` before `uv build` for robustness:

  ```yaml
  run: |
    rm -rf dist/
    uv build
    uv run --isolated --with dist/orbitcloud_graviton-*.whl python -c "
    ...
  ```

- **[.github/workflows/build.yml, release job]** The release job uses `commitizen-tools/commitizen-action@master` which installs commitizen via pip in its own environment. With `version_provider = "pep621"`, commitizen reads the version from `[project].version` in `pyproject.toml`. This should work correctly since commitizen's pep621 provider simply parses the TOML file without needing Poetry or uv. However, two observations:
  1. The release job no longer has Python explicitly set up (the old workflow had `actions/setup-python`). The `commitizen-action` manages its own Python, so this is likely fine, but it is worth verifying in a test run.
  2. After commitizen bumps the version, it updates `[project].version` in `pyproject.toml` and `VERSION`. The `uv.lock` file will become stale (it contains the old version). This won't break anything at runtime, but the lock file will drift from `pyproject.toml` until the next `uv lock` or `uv sync`. Consider adding `uv lock --no-install` as a post-bump step, or accept the drift since lock files are regenerated on `uv sync`.

### Suggestions (Consider)

- **[pyproject.toml:137]** `tool.ruff.target-version` is set to `py311` but `requires-python` is `>=3.12`. Consider updating to `py312` to enable pyupgrade and other rules to target the actual minimum Python version:

  ```toml
  target-version = "py312"
  ```

- **[Makefile:15-16]** There are three consecutive blank lines between the `install-precommit` target and the "Local development" section header (lines 15-17). This is a cosmetic leftover from removing the `install-poly` target. Reduce to one or two blank lines to match the rest of the file's style.

- **[.github/workflows/build.yml:26-35]** The smoke test imports only from `components/`. Consider adding one import from `bases/` to verify both source trees are included in the wheel:

  ```python
  from orbitcloud_graviton.landing_zone import LandingZone
  ```

  This provides broader coverage of the hatchling `packages` configuration.

- **[pyproject.toml:48-52]** The hatchling `packages` configuration uses directory-based discovery (`bases/orbitcloud_graviton`, `components/orbitcloud_graviton`). This is a significant improvement over the old Poetry config because:
  1. New sub-packages are automatically included without editing `pyproject.toml`.
  2. The old config was missing `bases/orbitcloud_graviton/firewall` and had a duplicate `pulumi_jinja` entry. Both issues are now resolved.

  Just verify that hatchling correctly merges the two `orbitcloud_graviton` trees into one namespace in the wheel. The fact that neither `bases/orbitcloud_graviton/__init__.py` nor `components/orbitcloud_graviton/__init__.py` exists (confirmed) means this is a proper implicit namespace package, which hatchling handles correctly.

### Praise

- Clean removal of all Poetry artifacts from `pyproject.toml`, `Makefile`, and `.github/workflows/build.yml`. The diff is tight and methodical.
- The switch from explicit per-package Poetry includes to hatchling directory-based discovery is a real improvement. It eliminates the manual maintenance burden and fixes the missing `firewall` base and duplicate `pulumi_jinja` entry from the old config.
- The CI workflow is dramatically simplified -- from 50+ lines with manual caching to ~15 lines. The `astral-sh/setup-uv@v5` with `enable-cache: true` handles caching automatically.
- Smart addition of the smoke test step. Testing the wheel in an isolated environment catches packaging issues that unit tests never would.
- Correct use of `version_provider = "pep621"` for commitizen, eliminating the version duplication between `[tool.poetry].version` (which was stale at `0.70.0`) and `[tool.commitizen].version`. Now there is a single source of truth at `[project].version = "0.89.0"`.
- The `dependency-groups` section correctly uses PEP 735 for dev dependencies, which is the modern standard that uv supports natively.
- Dependency version constraints were faithfully translated from Poetry's caret syntax to PEP 440 compatible ranges.

## Verification Checklist

| Check | Result |
|-------|--------|
| `[project]` section complete (name, version, requires-python, deps, authors) | PASS |
| PEP 735 `[dependency-groups]` for dev deps | PASS |
| Hatchling build backend configured | PASS |
| Hatchling packages point to both bases/ and components/ | PASS |
| commitizen `version_provider = "pep621"` | PASS |
| commitizen `version_files` no longer includes `pyproject.toml:^version` | PASS |
| No Poetry artifacts in pyproject.toml | PASS |
| No Poetry references in Makefile | PASS |
| No Poetry references in build.yml | PASS |
| No Poetry references in pre-commit config | **FAIL** (line 29) |
| `poetry.lock` deleted | PASS |
| `poetry.toml` deleted | PASS |
| `uv.lock` exists | PASS |
| `.python-version` exists (3.13.3) | PASS |
| `install-poly` Makefile target removed | PASS |
| `pulumi package gen-sdk` removed from install | PASS |
| Smoke test imports exist and are exported from `__init__.py` | PASS |
| No namespace `orbitcloud_graviton/__init__.py` at root level | PASS |
| All 40 sub-packages discoverable by hatchling | PASS |

## Summary

**Verdict: REQUEST CHANGES** -- one critical issue blocks merge.

The migration is thorough and well-executed. The single blocking issue is the stale `poetry run` reference in `.pre-commit-config.yaml` line 29, which will break the pyright pre-commit hook for anyone who has completed the uv migration. This is a one-line fix.

The important items (ruff upper bound, stale dist cleanup, uv.lock drift after commitizen bump) are worth addressing but are not merge-blockers. The suggestions (ruff target-version, smoke test breadth, cosmetic blank lines) are optional improvements.

Estimated effort to address all feedback: 15-30 minutes.

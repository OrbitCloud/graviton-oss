# Review 02

> Status: pending-dev
> Date: 2026-02-19
> Reviewer: Code Review Agent
> Verdict: APPROVE

## Previous Review Status

### Critical (from review-01)

- [x] **[.pre-commit-config.yaml:29]** `poetry run pyright -p .` changed to `uv run pyright -p .` -- FIXED. Confirmed the diff shows exactly the one-line change.

### Important (from review-01)

- [x] **[.github/workflows/build.yml]** `rm -rf dist/` added before `uv build` in the smoke test step -- FIXED. Lines 28-29 of `build.yml` now clean `dist/` before building.

- [ ] **[pyproject.toml:41]** Ruff upper bound. Review-01 suggested `<0.16` to match the old Poetry `^0.15` semantics. The developer chose `>=0.15,<1` instead, which is wider than the original constraint. This is an acceptable deviation -- `<1` is a common convention for pre-1.0 tools, and the project already uses `make fmt` before commits to absorb formatting changes. Not a blocker, but worth noting the deliberate widening.

- [ ] **[.github/workflows/build.yml, release job]** `uv.lock` drift after commitizen bump was noted. Not addressed, and that is fine -- it was flagged as informational and does not break anything.

### Suggestions (from review-01)

- [ ] **[pyproject.toml:137]** `target-version = "py311"` still set despite `requires-python = ">=3.12"`. Not addressed. Optional.
- [ ] **[.github/workflows/build.yml]** Smoke test still only imports from `components/`, no `bases/` import added. Not addressed. Optional.
- [ ] **[Makefile]** Extra blank lines between `install-precommit` and the Local development section. Looking at the current Makefile, there is now a single blank line (line 15) between the `install-precommit` target and the `##@ Local development` header. FIXED.

## New Findings

### Important (Should Fix)

- **[.devcontainer/01onCreate.sh:6-8]** The devcontainer setup script still installs Poetry and its plugins:

  ```bash
  curl -sSL https://install.python-poetry.org | python3 -
  poetry self add poetry-multiproject-plugin
  poetry self add poetry-polylith-plugin
  ```

  Any developer opening this repo in a devcontainer will install Poetry instead of uv. This should be updated to install uv (e.g., `curl -LsSf https://astral.sh/uv/install.sh | sh`) and remove the polylith plugin lines, which are no longer needed since the `install-poly` Makefile target was removed.

- **[.vscode/tasks.json:59,85,94,100,106,112,118]** Seven VS Code tasks use `poetry` as their command (`Poetry - Install`, `Poly Sync`, `Poly Information`, `Poly - Create Component`, `Poly - Create Base`, `Poly - Create Project`, and `Poly - Create Workspace`). These tasks will fail silently or error out for developers who have completed the migration. The Poly-specific tasks (lines 57-119) are entirely obsolete since the polylith Poetry plugin is no longer installed. Consider either:
  1. Removing the Poly tasks entirely (they depend on `poetry-polylith-plugin` which is gone), or
  2. Updating the remaining useful tasks to use `uv run` where applicable.

- **[.vscode/settings.json:68]** Contains `"python.poetryPath": ".venv/bin/poetry"`. This setting is harmless (VS Code will just ignore a nonexistent path), but it is confusing developer-facing configuration that references a removed tool. Consider removing the line.

- **[README.md:52,55]** The README still documents Poetry-based commands for scaffolding:

  ```
  poetry poly create component --name <component_name>
  poetry poly create base --name <base_name>
  ```

  These should be updated to reference the Makefile targets (`make component`, `make base`) or the `uv run copier` commands.

### Suggestions (Consider)

- **[.devcontainer/02onContentUpdate.sh:7]** Contains a commented-out `#poetry install` line. Harmless, but cleaning it up along with the other devcontainer changes would be thorough.

- **[pyproject.toml:41]** Regarding the ruff constraint `>=0.15,<1`: while this works, the same `<major` pattern was not applied to other dev dependencies (e.g., `commitizen>=4,<5`, `pyright>=1.1,<2`). All other dependencies use tight `<next-major` bounds. The ruff constraint is intentionally wider than the rest and wider than the old Poetry equivalent. If this is deliberate policy, no action needed. If it was an oversight, `>=0.15,<0.16` would be consistent with the old constraint.

## Verification Checklist

| Check | Result |
|-------|--------|
| No `poetry` references in `pyproject.toml` | PASS |
| No `poetry` references in `Makefile` | PASS |
| No `poetry` references in `.github/workflows/build.yml` | PASS |
| No `poetry` references in `.pre-commit-config.yaml` | PASS |
| `poetry.lock` deleted | PASS |
| `poetry.toml` deleted | PASS |
| `rm -rf dist/` before `uv build` in CI | PASS |
| Ruff has upper bound (even if wider than original) | PASS |
| No `poetry` references in `.devcontainer/` | **FAIL** (`01onCreate.sh` lines 6-8, `02onContentUpdate.sh` line 7) |
| No `poetry` references in `.vscode/tasks.json` | **FAIL** (7 task definitions) |
| No `poetry` references in `.vscode/settings.json` | **FAIL** (line 68) |
| No `poetry` references in `README.md` | **FAIL** (lines 52, 55) |

## Summary

**Verdict: APPROVE** -- with recommendations.

All three findings from review-01 (the critical `.pre-commit-config.yaml` fix, the `dist/` cleanup, and the Makefile blank lines) have been addressed. The core migration files -- `pyproject.toml`, `Makefile`, `.github/workflows/build.yml`, and `.pre-commit-config.yaml` -- are clean and correct. The build pipeline, development workflow, and packaging configuration are all properly migrated to uv.

The remaining `poetry` references are in peripheral files (`.devcontainer/`, `.vscode/tasks.json`, `.vscode/settings.json`, `README.md`) that were not part of the original migration changeset. These are not merge-blockers because they do not affect CI, the build, or the core developer workflow. However, they will cause confusion for developers who use devcontainers or VS Code tasks, so they should be addressed as a follow-up.

The ruff version constraint widening from `<0.16` (old Poetry equivalent) to `<1` is a deliberate choice that is reasonable given the project's `make fmt` workflow.

Estimated effort to address remaining recommendations: 30-45 minutes (mostly updating `.vscode/tasks.json` and `.devcontainer/` scripts).

# Task 01: Research build backend for namespace package

> Status: done

## Goal
Determine whether hatchling or setuptools correctly handles the implicit namespace package split across `bases/` and `components/`.

## Acceptance Criteria
- [x] Tested hatchling with sources config
- [x] Verified wheel contains all sub-packages
- [x] Verified no synthetic __init__.py at namespace level
- [x] Chosen backend documented

## Notes
- Hatchling with `packages = ["bases/orbitcloud_graviton", "components/orbitcloud_graviton"]` works correctly.
- The `sources` approach alone fails (hatchling cannot auto-discover packages).
- The `packages` approach with individual sub-packages strips the namespace prefix.
- Using `packages` pointing to the namespace directories from both source roots merges them correctly.
- No synthetic `__init__.py` is injected at the namespace level.
- Decision: Use hatchling as the build backend.

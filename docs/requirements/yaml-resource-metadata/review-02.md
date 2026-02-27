# Review 02

> Status: pending-dev
> Date: 2026-02-27
> Reviewer: Code Review Agent
> Verdict: APPROVE

## Previous Review Status

- [x] Issue from review-01 (Important #1): Cross-system prefix check for different-path resources -- ADDRESSED. The migration itself resolves the underlying data inconsistencies (`dnsr,` -> `dnsr`, `stbc` -> `stctr`), so the cross-system divergence that motivated this finding no longer exists. Resources like `Zone`, `RecordSet`, and `PrivateRecordSet` now live in their correct Pulumi module YAML files (`dns.yaml`, `privatedns.yaml`) and the v1 path is derived automatically.
- [x] Issue from review-01 (Important #2): `pytest.raises(Exception)` too broad in snapshot tests -- NOT IN SCOPE for Phase 2 (snapshot tests were not modified). The test file `test_yaml_metadata.py` correctly uses `pytest.raises(ValueError, match=...)` for its error handling tests.

## Review Scope

Phase 2: Full YAML migration. Reviewed all unstaged changes on branch `feature/yaml-resource-metadata` against `main`.

**Files reviewed:**
- `components/orbitcloud_graviton/az_lib/metadata/loader.py` (new)
- `components/orbitcloud_graviton/az_lib/metadata/services/*.yaml` (29 new files)
- `components/orbitcloud_graviton/az_lib/helpers.py` (import change)
- `components/orbitcloud_graviton/az_lib/meta.py` (import change)
- `components/orbitcloud_graviton/az_lib/naming_v1.py` (import change)
- `components/orbitcloud_graviton/az_lib/_prefixes.py` (deleted)
- `components/orbitcloud_graviton/az_lib/metadata/azure.py` (deleted)
- `test/components/orbitcloud_graviton/az_lib/test_yaml_metadata.py` (new)
- `pyproject.toml` (pyyaml dependency added)

## Verification Results

| Check | Result |
|-------|--------|
| `make test` (548 tests) | PASS |
| `make pyright` (0 errors) | PASS |
| `make lint` (ruff check + format) | PASS |
| Dangling imports to `_prefixes` or `metadata.azure` | None found |
| Snapshot tests still pass against YAML-backed data | PASS |

## New Findings

### Critical (Must Fix)

None.

### Important (Should Fix)

1. **[pyproject.toml:85] `pyyaml` is listed out of alphabetical order.**
   The dependency `pyyaml = "^6.0"` is inserted after `pydantic` but before `pydantic-settings`, breaking the alphabetical ordering convention used throughout the file. It should be placed after `pydantic-settings` and before `python`.

   This is cosmetic but consistent ordering makes the dependency list scannable and reduces merge conflicts.

### Suggestions (Consider)

1. **[loader.py:160] Consider using `Path.read_text()` instead of `open(path)` for consistency.**
   Lines 160-161 and 174-175 use `with open(path) as f: raw = yaml.safe_load(f)`. The `Path` object is already available; `yaml.safe_load(path.read_text())` would be slightly more concise and idiomatic for pathlib-based code. This is purely a style preference.

2. **[loader.py:104-124] The `_V1_MODULE_PATH_OVERRIDES` and `_V1_EXCLUDE_ENTRIES` mappings are well-documented but could benefit from a brief comment explaining the general principle.**
   The overrides exist because some Pulumi SDK module paths do not match the auto-derived `_pascal_to_snake()` output. A one-line comment like "# These exist where the Pulumi SDK module name differs from PascalCase-to-snake_case of the YAML class name" at the top of the overrides section would help future readers. The existing inline comments per entry are already good.

3. **[meta.py:101] `resource_meta()` mutates the cached `_azure_resource_meta` dict in-place.**
   Line 101 (`resource_meta["pulumi_resource"] = pulumi_resource`) injects a `PulumiResource` instance into the shared cached dict on every call. This is a pre-existing issue (not introduced by this PR), but worth noting since the data is now loaded once from YAML and cached at module level. After the first call for a given resource, the dict entry will contain a stale `pulumi_resource` key from a previous invocation. In practice this is harmless because `Pydantic.model_validate()` on line 103 creates a new model instance each time, and the `pulumi_resource` value is overwritten on each call. However, it means the cached dict is progressively polluted with non-YAML data. A future cleanup could use `{**resource_meta, "pulumi_resource": pulumi_resource}` to avoid mutation.

### Praise

- **Clean separation of concerns.** The `loader.py` module has a single responsibility: load YAML, validate with Pydantic, and expose the same data structures as before. The Pydantic schemas (`NamingRuleSchema`, `ResourceSchema`, `ServiceFileSchema`, `RegionSchema`, `RegionsFileSchema`) with `extra="forbid"` provide strict validation that will catch typos and schema drift immediately.

- **All four known bugs are fixed.**
  - `stbc` -> `stctr` in `storage.yaml` (BlobContainer prefix now matches v1 production value)
  - `dnsr,` -> `dnsr` in `dns.yaml` (trailing comma removed from RecordSet prefix)
  - `Micrsoft` -> `Microsoft` in `containerregistry.yaml` (`azure_namespace` is now correctly `Microsoft.ContainerRegistry`)
  - `AppServicePlan` in `web.yaml` now has the proper `naming:` wrapper (was previously a bare `{"prefix": "asp"}` dict without the naming key)

- **Correct handling of the v1/v2 duality.** The `_V2_SERVICE_FILES` set ensures only the original 18 v2 namespaces appear in `_azure_resource_meta`, while the flat `RESOURCE_PREFIXES` is built from ALL YAML files (including `dns.yaml`, `privatedns.yaml`, `applicationinsights.yaml`, `monitor.yaml`, `compute.yaml`, `dnsresolver.yaml`, `managedidentity.yaml`, `recoveryservices.yaml`, `dbforpostgresql.yaml`, and `random.yaml`). This correctly expands v1 coverage from 67 to 81+ entries while keeping v2 backward-compatible.

- **Thoughtful handling of alias entries.** The `_V1_EXCLUDE_ENTRIES` set correctly prevents v2-only class names (like `insights.Component`, `insights.Diagnosticsetting`, `eventhub.Eventhub`) from generating duplicate or incorrect v1 module paths, while the corresponding v1-correct entries come from their proper YAML files (`applicationinsights.yaml`, `monitor.yaml`, and the `EventHub` entry in `eventhub.yaml` with its override).

- **Data integrity verified by cross-referencing.** I manually compared every prefix in the YAML files against the deleted `_prefixes.py` and `metadata/azure.py` source. All values are preserved exactly, with the four intentional bug fixes applied.

- **No per-call I/O.** The `_load_all()` function is called once at module import time (line 284), and the results are cached in module-level variables. The `sorted(_SERVICES_DIR.glob("*.yaml"))` ensures deterministic load order. This is the correct pattern for configuration data.

- **`_pascal_to_snake` handles all edge cases correctly.** Verified against 17 class names including tricky cases: `P2sVpnGateway` -> `p2s_vpn_gateway`, `DnssecConfig` -> `dnssec_config`, `HubVirtualNetworkConnection` -> `hub_virtual_network_connection`.

- **Good test coverage for the new loader.** `test_yaml_metadata.py` covers: file loading, schema validation, error handling (empty YAML, missing fields, extra fields), data integrity checks for the four known fixes, count assertions, and region loading. The existing 320 snapshot tests from Phase 1 serve as an additional safety net and all pass against the YAML-backed data.

- **Non-Azure resources handled correctly.** `random.yaml` has no `azure_namespace` field, is excluded from `_V2_SERVICE_FILES`, and uses a `_V1_MODULE_PATH_OVERRIDES` entry to produce `pulumi_random.random_password` instead of `pulumi_azure_native.random.random_password`.

## Summary

**Overall assessment: APPROVE**

This is a well-executed YAML migration. The loader design is clean and correct: Pydantic validates every YAML file at import time with `extra="forbid"`, the dual v1/v2 data structures are rebuilt faithfully, all four known bugs are fixed, and 548 tests pass (including the 320 Phase 1 snapshot tests that serve as the migration safety net). The `_pascal_to_snake` conversion handles all edge cases, the override/exclude mechanisms for v1 path derivation are well-documented, and there are no dangling imports to the deleted files. pyright reports zero errors.

The one "Important" finding is a minor alphabetical ordering issue in `pyproject.toml`. The three "Suggestions" are all optional improvements for code hygiene.

**Estimated effort to address feedback:** 5 minutes for the Important item, optional for Suggestions.

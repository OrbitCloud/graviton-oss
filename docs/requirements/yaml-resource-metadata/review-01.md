# Review 01

> Status: addressed
> Date: 2026-02-27
> Reviewer: Code Review Agent
> Verdict: APPROVE

## Previous Review Status

N/A -- this is the first review.

## New Findings

### Critical (Must Fix)

None.

### Important (Should Fix)

1. **[test_metadata_snapshot.py:925-978, 1099-1116] Cross-system prefix check does not cover "different path" resources.**
   The `V1_TO_V2_MAPPING` dictionary (used by `test_cross_system_prefix_consistency`) deliberately excludes seven resources where the v1 module path and v2 namespace key differ (e.g., `insights.Component` vs `applicationinsights.component`). These exclusions are documented in `v2_with_v1_counterpart_different_path` inside `test_cross_system_v2_only_resources`, but their prefix values are **never compared** against each other.

   This means if someone changes the v2 prefix for `insights.Component` from `appi` to something else, only the v2 snapshot test would catch it -- the cross-system consistency test would not flag the divergence from v1.

   Most of these actually have matching prefixes (verified manually), but one already diverges: `network.RecordSet` has `dnsr,` (trailing comma) in v2 while v1 has `dnsr`. This should be explicitly documented as a known discrepancy alongside BlobContainer.

   **Suggested fix:** Add a new test `test_cross_system_prefix_consistency_different_paths` that maps these seven pairs and asserts their prefixes match (or documents known discrepancies like `RecordSet`). Example:

   ```python
   V1_TO_V2_DIFFERENT_PATH_MAPPING = {
       "pulumi_azure_native.applicationinsights.component": ("insights", "Component"),
       "pulumi_azure_native.monitor.diagnostic_setting": ("insights", "Diagnosticsetting"),
       "pulumi_azure_native.eventhub.event_hub": ("eventhub", "Eventhub"),
       "pulumi_azure_native.dns.zone": ("network", "Zone"),
       "pulumi_azure_native.dns.record_set": ("network", "RecordSet"),
       "pulumi_azure_native.privatedns.private_record_set": ("network", "PrivateRecordSet"),
       "pulumi_azure_native.web.app_service_plan": ("web", "AppServicePlan"),
   }
   ```

   Then parametrize a test that compares v1 prefix against v2 prefix for each, with `RecordSet` listed in `KNOWN_PREFIX_DISCREPANCIES`.

2. **[test_metadata_snapshot.py:1286] `pytest.raises(Exception)` is too broad for the extra-fields test.**
   The `test_extra_fields_forbidden` test uses `pytest.raises(Exception)` with a `# noqa: B017` suppression. While the noqa is acknowledged, this could mask unrelated errors. Since this is a Pydantic v2 model with `extra="forbid"`, the expected exception is `pydantic.ValidationError`.

   **Suggested fix:** Replace `Exception` with `pydantic.ValidationError` and remove the noqa comment. This makes the assertion more precise.

### Suggestions (Consider)

1. **[test_metadata_snapshot.py:601-606] The `_MockPulumiClass` could be a `dataclass` or `NamedTuple` for clarity.**
   Currently it is a plain class that sets `self.__module__` in `__init__`. This works, but a one-liner `types.SimpleNamespace` or a brief docstring explaining *why* `__module__` is the key attribute would help future readers understand that `get_prefix()` relies on `resource_type.__module__` for lookup. This is minor -- the current approach is functional and the docstring already explains the intent.

2. **[test_metadata_snapshot.py:800-840] Consider adding v2 naming tests for edge-case naming rules (alphanumeric, lowercase, max_length).**
   The v2 naming expected values already cover the alphanumeric case (`ContainerRegistry` -> `CrWorkloadTestNeu01`, `StorageAccount` -> `stworkloadtestneu01`), which is good. However, `max_length` truncation is not exercised because the test inputs produce names shorter than 60 characters (the only max_length constraint is on `ManagedEnvironment` at 60 chars, and `cae-workload-test-neu-01` is 24 chars). While this is not strictly a Phase 1 gap (the snapshot is correct for the given inputs), a follow-up test with a longer workload name that triggers truncation would strengthen the safety net.

3. **[test_metadata_snapshot.py:490-503] The parametrize `ids` lambda returns empty string for non-string params.**
   The `ids=lambda p: p if isinstance(p, str) else ""` pattern in `test_v2_metadata_snapshot` produces test IDs like `test_v2_metadata_snapshot[app--]` where the empty strings make test output harder to read. Consider using `ids=lambda ns, cls, _: f"{ns}.{cls}"` or a custom id function that produces readable names.

### Praise

- **Excellent snapshot data accuracy.** I cross-checked every entry in `V1_PREFIX_SNAPSHOT` against `_prefixes.py` and every entry in `V2_METADATA_SNAPSHOT` against `metadata/azure.py`. All values match exactly, including edge cases like `caecert-` (trailing hyphen), the `Micrsoft` typo, and the `dnsr,` trailing comma.

- **Thorough integrity guards.** The count tests (`test_v1_prefix_count`, `test_v2_namespace_count`, `test_v2_resource_count_per_namespace`) and key-set assertions (`test_v1_snapshot_keys_match_source`) mean that adding or removing a resource from the source dicts will be caught even if the individual parametrized snapshot test is not updated. This is a belt-and-suspenders approach that significantly strengthens the safety net.

- **Complete documentation of v2 unreachable resources.** The `V2_UNTESTABLE_RESOURCES` dict with detailed explanations for each skipped resource is exactly the kind of documentation that prevents future confusion. Each entry explains the root cause (namespace mismatch, class name mismatch, missing naming wrapper) clearly.

- **Good use of parametrized tests.** Testing every entry via `@pytest.mark.parametrize` over `sorted(RESOURCE_PREFIXES.keys())` ensures that new entries added to the source dict will cause the count/key-set tests to fail, prompting the developer to update the snapshot. This is the right pattern for snapshot testing.

- **End-to-end naming tests verify the full code path.** The v1 naming tests go through `resource_namer()` -> `get_prefix()` -> `location_abbr()` and the v2 tests go through `resource_meta()` -> `autoname()` -> `fmt_name()` -> `location_abbr()`, which means the tests exercise the complete naming pipeline, not just the data lookups.

- **API contract tests lock down function signatures and error behavior.** The `inspect.signature()` assertions on `get_prefix`, `resource_namer`, `location_abbr`, and `resource_meta` will catch any accidental parameter renames or return type changes during migration.

- **All 422 tests pass (320 new + 102 existing).** No regressions introduced. Test execution completes in ~5 seconds.

## Summary

**Overall assessment: APPROVE**

This is a high-quality Phase 1 implementation that provides a strong safety net for the upcoming YAML migration. The snapshot data is accurate, the test coverage is comprehensive across both v1 and v2 systems, and the known issues (BlobContainer discrepancy, unreachable v2 resources, source code bugs) are well-documented.

The one "Important" finding -- the missing cross-system prefix comparison for resources with different namespace paths -- is a real gap in the safety net but is partially mitigated by the individual snapshot tests that would catch value changes in either system independently. Adding that test would make the safety net complete.

**Estimated effort to address feedback:** 30 minutes for the Important items, optional for Suggestions.

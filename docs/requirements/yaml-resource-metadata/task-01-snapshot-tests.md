# Task 01: Phase 1 - Pre-Migration Snapshot Tests

> Status: done

## Goal
Create comprehensive snapshot and parametrized tests that lock down the exact current behavior of both v1 and v2 naming systems, regions, cross-system consistency, and API contracts.

## Acceptance Criteria
- [x] Snapshot test for all v1 prefixes (RESOURCE_PREFIXES)
- [x] Snapshot test for all v2 metadata (_azure_resource_meta)
- [x] Snapshot test for all regions (_azure_regions) with LOCATION_ABBR subset check
- [x] End-to-end naming tests for every resource type via v1 API (resource_namer)
- [x] End-to-end naming tests for every resource type via v2 API (resource_meta autoname)
- [x] Cross-system consistency test (v1 vs v2 prefix matching)
- [x] API contract tests (signatures, return types, error behavior)
- [x] All tests pass with `make fmt && make lint && make test`

## Notes
- New test file: test/components/orbitcloud_graviton/az_lib/test_metadata_snapshot.py
- 320 new tests added, all passing
- No existing source code was modified
- Documented all v1/v2 discrepancies and untestable v2 resources

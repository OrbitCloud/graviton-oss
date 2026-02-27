# Task 02: YAML Migration (Phase 2)

> Status: done

## Goal
Replace the dual Python-dict-based resource metadata systems (_prefixes.py + metadata/azure.py) with a unified set of YAML files and a Python loader module.

## Acceptance Criteria
- [x] PyYAML added to pyproject.toml dependencies
- [x] YAML files created in metadata/services/ for all Azure service namespaces
- [x] regions.yaml created with all region data
- [x] YAML loader module (metadata/loader.py) created with Pydantic validation
- [x] meta.py updated to use YAML-backed _azure_resource_meta
- [x] helpers.py updated to use YAML-backed _azure_regions
- [x] naming_v1.py updated to use YAML-backed RESOURCE_PREFIXES
- [x] _prefixes.py deleted
- [x] metadata/azure.py deleted
- [x] Snapshot tests updated to import from new sources
- [x] New YAML validation tests added
- [x] All tests pass (548 total)
- [x] make fmt, make lint, make test, make pyright all pass
- [x] Known fixes applied: stbc->stctr, dnsr,->dnsr, Micrsoft->Microsoft, AppServicePlan naming wrapper

## Notes
- 81 resources in RESOURCE_PREFIXES (up from 67, as new resources from v2 are now also available in v1)
- 27 YAML files in services/ directory (one per Pulumi module, plus regions.yaml and random.yaml)
- AppServicePlan is now testable via resource_meta().autoname() (was broken before due to missing naming wrapper)
- Resources that were previously only in v2 under different namespace keys (Zone, RecordSet, PrivateRecordSet) are now in their correct Pulumi module YAML files (dns.yaml, privatedns.yaml)

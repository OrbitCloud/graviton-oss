# YAML Resource Metadata Requirements

## Overview

Replace the dual Python-dict-based resource metadata systems (`_prefixes.py` + `metadata/azure.py`) with a unified set of YAML files — one per Azure service namespace. This eliminates the legacy v1/v2 split and provides a single source of truth for resource naming rules, Azure namespace info, and DNS zones.

**Reference:** [Azure CAF Resource Abbreviations](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/azure-best-practices/resource-abbreviations)

## Goals

- Single source of truth for all Azure resource metadata (prefixes, naming rules, namespaces, DNS zones)
- YAML files split by Azure service namespace — human-readable, easy to maintain, easy to review in PRs
- Unified Python API that replaces both `naming_v1.py` functions and `meta.py` functions
- Zero prefix value changes (resources would be recreated in Azure)

## User Stories

- As a CDK developer, I want to add a new Azure resource type by editing a YAML file instead of modifying Python dicts in multiple places.
- As a CDK developer, I want one naming function (not separate v1/v2 code paths) to generate compliant resource names.
- As a CDK maintainer, I want resource metadata in a format that's easy to diff, review, and validate with a schema.

## Implementation Phases

This migration is safety-critical (wrong prefixes = resource recreation). The work is split into two phases: **first lock down current behavior with tests**, then migrate.

### Phase 1: Pre-Migration Test Coverage

Comprehensive snapshot tests that capture the exact current behavior of both v1 and v2 systems. These tests act as a safety net — if any prefix, naming rule, or metadata value changes during migration, they will fail.

- [ ] **Snapshot test for all v1 prefixes:** Iterate every entry in `RESOURCE_PREFIXES` and assert the exact prefix, alphanumeric, lowercase, and max_length values. This is a parametrized test over all ~60 entries — not just a few samples.
- [ ] **Snapshot test for all v2 metadata:** Iterate every resource in `_azure_resource_meta` and assert the full metadata (naming rules, namespace, sub_resource_name, public_dns_zone, private_dns_zone).
- [ ] **Snapshot test for all regions:** Assert every entry in `_azure_regions` (and verify `LOCATION_ABBR` in `_prefixes.py` is a subset).
- [ ] **End-to-end naming tests for every resource type via v1 API:** Parametrized test calling `resource_namer()` for every resource in `RESOURCE_PREFIXES` with a fixed workload/env/location/instance, asserting the exact output string.
- [ ] **End-to-end naming tests for every resource type via v2 API:** Parametrized test calling `resource_meta(PulumiClass).autoname(stack)` for every resource in `_azure_resource_meta`, asserting exact output strings.
- [ ] **Cross-system consistency test:** For resources that exist in both v1 and v2, assert that their prefix values match (flag any discrepancies like `stctr` vs `stbc`).
- [ ] **API contract tests:** Assert function signatures, return types, and error behavior (`ValueError` on unknown resource, `ValueError` on unknown region).

All Phase 1 tests must pass on the current codebase before any migration work begins.

### Phase 2: Migration

## Functional Requirements

### Must Have (P0)

- [ ] Create YAML files in `components/orbitcloud_graviton/az_lib/metadata/services/` — one file per Azure service namespace:
  - `app.yaml` (Container Apps)
  - `appconfiguration.yaml`
  - `authorization.yaml`
  - `cognitiveservices.yaml`
  - `containerregistry.yaml`
  - `eventgrid.yaml`
  - `eventhub.yaml`
  - `insights.yaml` (App Insights / Monitor)
  - `keyvault.yaml`
  - `network.yaml`
  - `operationalinsights.yaml`
  - `providerhub.yaml`
  - `resources.yaml`
  - `search.yaml`
  - `servicebus.yaml`
  - `sql.yaml`
  - `storage.yaml`
  - `web.yaml`
  - `regions.yaml` (Azure regions with abbreviations)
  - Plus any additional files needed for resources currently only in `_prefixes.py` (dns, dnsresolver, managedidentity, dbforpostgresql, compute, recoveryservices, random)

- [ ] Each service YAML file must follow a consistent schema. Example (`keyvault.yaml`):
  ```yaml
  azure_namespace: Microsoft.KeyVault
  resources:
    Vault:
      naming:
        prefix: kv
        alphanumeric: true
        max_length: 24
      namespace: Microsoft.KeyVault/vaults
      sub_resource_name: vault
      public_dns_zone: vault.azure.net
      private_dns_zone: privatelink.vaultcore.azure.net
    Secret:
      naming:
        prefix: kvs
  ```

- [ ] `regions.yaml` schema:
  ```yaml
  regions:
    northeurope:
      name: North Europe
      abbr: neu
    westeurope:
      name: West Europe
      abbr: weu
    # ...
  ```

- [ ] Create a YAML loader module (`metadata/loader.py` or similar) that:
  - Reads all YAML files from the `services/` directory at import time
  - Builds the same hierarchical structure currently in `_azure_resource_meta`
  - Builds a flat Pulumi-module-path-keyed lookup (replacing `RESOURCE_PREFIXES`)
  - Loads region data (replacing both `LOCATION_ABBR` and `_azure_regions`)
  - Caches the result (load once, reuse)

- [ ] Preserve all existing prefix values exactly as-is (critical — changing prefixes causes resource recreation)

- [ ] Merge resources that exist only in `_prefixes.py` but not in `metadata/azure.py` into the YAML files. These resources currently only in the legacy system:
  - `monitor.diagnostic_setting` (already in v2 as insights.Diagnosticsetting — verify)
  - `web.app_service_plan` (partially in v2 as web.AppServicePlan but missing `naming` wrapper)
  - `web.app_service` (verify against v2 web.WebApp)
  - `network.network_rule_set` entries (eventhub, servicebus)
  - `dns.zone`, `dns.record_set`
  - `privatedns.private_record_set`
  - `network.vpn_gateway`, `network.virtual_network_gateway`, `network.virtual_network_gateway_connection`, `network.local_network_gateway`
  - `dnsresolver.*` (dns_resolver, inbound_endpoint, outbound_endpoint, dns_forwarding_ruleset)
  - `managedidentity.user_assigned_identity`
  - `dbforpostgresql.server`, `dbforpostgresql.administrator`, `dbforpostgresql.configuration`
  - `sql.firewall_rule`, `sql.server_dns_alias`, `sql.elastic_pool`, `sql.job_agent`, `sql.job_target_group`, `sql.job`, `sql.job_step`
  - `compute.virtual_machine`, `compute.disk`
  - `network.network_interface`, `network.azure_firewall`, `network.firewall_policy`, `network.dnssec_config`, `network.route_table`
  - `recoveryservices.vault`, `recoveryservices.protection_policy`
  - `pulumi_random.random_password`
  - `storage.file_service_properties`

- [ ] Unify the Python API — keep function signatures compatible but route through one data source:
  - `resource_meta(obj)` — primary API, returns `AzureResourceMetadata` (keep existing signature)
  - `resource_meta(obj).autoname(stack)` — primary naming API (keep existing)
  - `get_prefix(resource_type)` — keep as thin wrapper for backwards compat, backed by YAML data
  - `resource_namer(resource_type, workload_name, env, location, instance_number)` — keep as thin wrapper for backwards compat, backed by YAML data
  - `location_abbr(location)` — backed by regions.yaml

- [ ] All existing tests must pass without modification (the test file uses `resource_meta().autoname()`)

- [ ] Delete `_prefixes.py` after migration is complete
- [ ] Delete or deprecate `naming_v1.py` (keep `get_prefix` and `resource_namer` as compatibility wrappers, potentially moved into the unified module)

### Should Have (P1)

- [ ] Add a JSON Schema or Pydantic validation for the YAML files so malformed entries are caught early
- [ ] Add a test that validates all YAML files load correctly and every resource has at minimum a `naming.prefix` field
- [ ] Include `package.json`-style `$schema` comment or similar in YAML files for editor support
- [ ] Fix the typo in v2 metadata: `"Micrsoft.ContainerRegistry"` → `"Microsoft.ContainerRegistry"` (line 416 of azure.py)

### Nice to Have (P2)

- [ ] Add a CLI/script to diff current YAML prefixes against the Microsoft CAF guide and report missing resources
- [ ] Include YAML comments linking each resource to its CAF documentation URL

## Non-Functional Requirements

- **Performance:** YAML files should be loaded once at module import time and cached. No per-call file I/O.
- **Security:** No impact — this is internal metadata only.
- **Backwards Compatibility:** Critical. All existing prefix strings must remain identical. The public API surface (`get_prefix`, `resource_namer`, `resource_meta`, `location_abbr`, `autoname`) must continue to work with existing call sites:
  - `azure_base.py:64` — `resource_namer(resource_type, ...)`
  - `appservice_plan.py:97` — `resource_namer(web.AppServicePlan, ...)`
  - `private_endpoint.py` — `resource_meta(obj)`
  - `test_resource_naming.py` — `resource_meta(...).autoname(stack)`

## Edge Cases & Error Handling

| Scenario | Expected Behavior |
|----------|-------------------|
| YAML file missing for a service namespace | Raise `FileNotFoundError` with helpful message at load time |
| Resource type not found in YAML data | Raise `ValueError` (same as current behavior) |
| YAML file has invalid schema (missing `naming.prefix`) | Raise validation error at load time, not at call time |
| Pulumi module path with version suffix (e.g., `_v20241002preview`) | Strip version suffix before lookup (preserve current normalization logic) |
| `pulumi_random.random_password` (non-Azure resource) | Support via a `random.yaml` or `_other.yaml` file — the loader must handle non-`pulumi_azure_native` packages |
| Duplicate prefix across resources | Allowed (already exists: `app` is used for both ContainerApp and WebApp; `vpng` for P2sVpnGateway and VpnGateway) |

## Affected Components

- `components/orbitcloud_graviton/az_lib/metadata/` — new `services/` directory with YAML files, new `loader.py`
- `components/orbitcloud_graviton/az_lib/metadata/azure.py` — to be replaced/deleted
- `components/orbitcloud_graviton/az_lib/_prefixes.py` — to be deleted
- `components/orbitcloud_graviton/az_lib/naming_v1.py` — to be refactored into compatibility wrappers
- `components/orbitcloud_graviton/az_lib/naming.py` — `ResourceNameRule` model stays as-is
- `components/orbitcloud_graviton/az_lib/meta.py` — update to use YAML-backed data instead of `_azure_resource_meta`
- `components/orbitcloud_graviton/az_lib/helpers.py` — update `location_abbr` to use YAML-backed regions
- `components/orbitcloud_graviton/az_lib/__init__.py` — update exports if module names change
- `test/components/orbitcloud_graviton/az_lib/test_resource_naming.py` — should pass as-is (add new validation tests)

## Out of Scope

- Adding new resource types not currently in the codebase (only migrate existing ones)
- Changing any prefix values
- Changing the naming pattern format (`{prefix}-{workload}-{env}-{location}-{instance}`)
- Migrating consumers of `resource_namer` to use `resource_meta().autoname()` (can be done later)

## Dependencies

- PyYAML or `pyyaml` (check if already a dependency; if not, add it)
- Pydantic (already used for `ResourceNameRule`, `AzureResourceMetadata`)

## Data Reconciliation Notes

The two existing systems have some inconsistencies that must be resolved during migration:

| Issue | Resolution |
|-------|------------|
| `_prefixes.py` has `stctr` for BlobContainer; `azure.py` has `stbc` | **Use `stctr`** — this is the v1 value actively used in production. Update v2's `stbc` to `stctr` during migration. |
| `_prefixes.py` has `"caecert-"` (trailing hyphen) for Certificate | Preserve exactly as-is |
| `azure.py` `_web.AppServicePlan` has `{"prefix": "asp"}` without `naming` wrapper | Fix during migration — wrap in `naming:` like all others |
| `azure.py` `_network.RecordSet` has `"dnsr,"` (trailing comma in prefix) | Likely a typo — verify against `_prefixes.py` which has `"dnsr"`. Fix if confirmed. |
| LOCATION_ABBR in `_prefixes.py` is dead code (never imported) | Drop it — `_azure_regions` in `azure.py` is the active source |
| `"Micrsoft.ContainerRegistry"` typo in azure.py line 416 | Fix to `"Microsoft.ContainerRegistry"` |

## Open Questions

- [ ] Is PyYAML already in the project dependencies, or do we need to add it?
- [x] For the `BlobContainer` prefix discrepancy (`stctr` vs `stbc`): **Resolved — use `stctr`** (the v1/production value).
- [ ] The `RecordSet` prefix `"dnsr,"` in `metadata/azure.py` has a trailing comma — is this intentional or a typo?
- [ ] Should `pulumi_random.random_password` be kept in scope, or dropped since it's not an Azure resource?

## Acceptance Criteria

### Phase 1 (Pre-Migration Tests)
- Snapshot tests cover 100% of entries in `RESOURCE_PREFIXES`, `_azure_resource_meta`, and `_azure_regions`
- Parametrized naming tests cover every resource type through both v1 and v2 APIs
- Cross-system consistency test identifies and documents all v1/v2 discrepancies
- All Phase 1 tests pass green on the current (unmodified) codebase

### Phase 2 (Migration)
- All Phase 1 snapshot and naming tests pass without modification after migration
- `_prefixes.py` is deleted
- `metadata/azure.py` Python dicts are replaced by YAML files
- Every resource that existed in either `_prefixes.py` or `metadata/azure.py` exists in exactly one YAML file
- `resource_meta(SomeAzureClass).autoname(stack)` produces identical output as before
- `resource_namer(SomeAzureClass, ...)` produces identical output as before
- `location_abbr("westeurope")` returns `"weu"` (and all other regions unchanged)
- YAML files are validated at load time (schema check)
- No file I/O on individual `resource_meta()` or `resource_namer()` calls (data is pre-loaded)

# Fix Duplicate Storage Account Resource Names

## Overview
When provisioning more than one storage account via `app_zone`, all accounts receive the same Pulumi `ComponentResource` name (`st-{workload_name}`), causing Pulumi to exit with a non-unique resource name error. The fix ensures each storage account gets a unique Pulumi resource name derived from its config.

## Goals
- Eliminate duplicate Pulumi resource name errors when multiple storage accounts are defined
- Make `StorageAccountConfig.name` a required field to enforce explicit, unique naming

## User Stories
As a platform engineer, I want to provision multiple storage accounts in a single app_zone deployment so that each workload can have dedicated storage without naming conflicts.

## Functional Requirements

### Must Have (P0)
- [ ] Incorporate `config.name` into the Pulumi `ComponentResource` name in `StorageAccount.__init__` (currently hardcoded to `f"st-{self.stack.workload_name}"`)
- [ ] Make `StorageAccountConfig.name` a required field (`str` instead of `str | None = None`)
- [ ] Add/update tests to verify that multiple storage accounts produce unique Pulumi resource names

### Should Have (P1)
- [ ] Add a validation rule (Pydantic validator) on `AppZoneBaseConfig.storage_accounts` to reject duplicate `name` values within the list

## Non-Functional Requirements
- **Backwards Compatibility:** This is a breaking change for any stack configs that omit `name` on a single storage account. Acceptable per user decision — configs must be updated to include `name`.
- **Security:** No impact.
- **Performance:** No impact.

## Edge Cases & Error Handling
| Scenario | Expected Behavior |
|----------|-------------------|
| Two storage accounts with the same `name` in config | Pydantic validation error at config load time with a clear message |
| Single storage account (name now required) | Works as before, but user must provide a `name` value |
| `name` omitted from config YAML | Pydantic validation error (field is required) |

## Affected Components
- `components/orbitcloud_graviton/az_storage/storage_account.py` — `StorageAccount.__init__` resource name + `StorageAccountConfig.name` field
- `bases/orbitcloud_graviton/app_zone/app_zone_base.py` — no code change expected, but integration tests should cover multi-storage
- Tests in `tests/` covering storage account provisioning

## Out of Scope
- Auditing other components for the same pattern (storage only per user decision)
- Auto-generating unique suffixes — user must provide explicit names

## Dependencies
- None beyond existing Pulumi Azure Native provider and Pydantic

## Open Questions
- None

## Acceptance Criteria
- Deploying an app_zone with 2+ storage accounts (each with a unique `name`) succeeds without duplicate resource name errors
- Deploying with duplicate `name` values produces a clear validation error
- Deploying with `name` omitted produces a clear validation error
- Existing tests pass; new tests cover multi-account scenarios

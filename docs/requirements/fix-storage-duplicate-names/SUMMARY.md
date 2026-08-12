# Summary: Fix Duplicate Storage Account Resource Names

## What was implemented

### 1. Made `StorageAccountConfig.name` a required field (P0)
**File:** `components/orbitcloud_graviton/az_storage/storage_account.py`

Changed `name: str | None = None` to `name: str`. This is a breaking change -- any config that previously omitted `name` will now fail validation with a clear Pydantic error.

### 2. Unique Pulumi ComponentResource names (P0)
**File:** `components/orbitcloud_graviton/az_storage/storage_account.py`

Changed the `super().__init__` name parameter from `f"st-{self.stack.workload_name}"` to `f"st-{self.config.name}"`. This ensures each storage account gets a unique Pulumi resource name derived from its explicit config name, preventing duplicate resource name errors when provisioning multiple storage accounts.

### 3. Duplicate name validator on AppZoneBaseConfig (P1)
**File:** `bases/orbitcloud_graviton/app_zone/app_zone_base.py`

Added a `@model_validator(mode="after")` on `AppZoneBaseConfig` that rejects duplicate `name` values in the `storage_accounts` list. This catches configuration errors at config load time with a clear message like: `storage_accounts contains duplicate name values: ['alpha']`.

## Tests added

### `test/components/orbitcloud_graviton/az_storage/test_storage_account.py` (5 tests)
- `TestStorageAccountConfigName::test_name_is_required` -- omitting name raises ValidationError
- `TestStorageAccountConfigName::test_name_provided` -- providing a name works
- `TestStorageAccountConfigName::test_name_cannot_be_none` -- None raises ValidationError
- `TestStorageAccountResourceNaming::test_resource_name_includes_config_name` -- URN contains config.name
- `TestStorageAccountResourceNaming::test_two_accounts_get_different_resource_names` -- two accounts produce distinct URNs

### `test/bases/orbitcloud_graviton/app_zone/test_app_zone_config.py` (5 tests)
- `test_no_storage_accounts_is_valid` -- None is accepted
- `test_single_storage_account_is_valid` -- single account works
- `test_unique_names_are_valid` -- multiple unique names work
- `test_duplicate_names_rejected` -- duplicate names raise ValidationError
- `test_empty_list_is_valid` -- empty list is accepted

## Decisions and trade-offs

- **Breaking change accepted**: Making `name` required is intentional per requirements. All existing usage in `containerapp_env.py` already passes `name`.
- **Test mocking**: Resource naming tests use `patch.object(StorageAccount, "_outputs")` to bypass the `_outputs` method that accesses mock-incompatible Pulumi output properties (e.g. `primary_endpoints.microsoft_endpoints`). This is a pragmatic choice -- the tests verify the ComponentResource URN, not the outputs.
- **App zone test imports**: The app_zone test stubs `orbitcloud_graviton.az_iam` to avoid the `asyncio.get_running_loop()` call in `_roles.py` during import. This follows the same pattern used by the existing `test_containerapp_env_storage.py`.

## Validation results

- `make fmt` -- passed (1 autofix applied)
- `make lint` -- passed (all checks passed)
- `make test` -- 615 passed, 4 skipped, 0 failures

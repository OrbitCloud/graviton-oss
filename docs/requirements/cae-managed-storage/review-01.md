# Review 01

> Status: addressed
> Date: 2026-02-26
> Reviewer: Code Review Agent
> Verdict: REQUEST CHANGES

## Previous Review Status

No previous reviews.

## New Findings

### Critical (Must Fix)

- **[components/orbitcloud_graviton/az_app/containerapp_env.py:326] `list_storage_account_keys` called with `Output[str]` arguments instead of plain `str`.**

  The `_environment_storage()` method calls `storage.list_storage_account_keys()` which expects plain `str` parameters (`account_name: Optional[str]`, `resource_group_name: Optional[str]`). However, it passes `sa.storage_account.name` and `self.stack.resource_group.name`, both of which are `pulumi.Output[str]`. This will fail at deploy time.

  The existing pattern in the codebase (`bases/orbitcloud_graviton/oracledb/oradb_base.py:68`) correctly uses the Output-aware variant:

  ```python
  storage_account_key: pulumi.Output[str] = storage.list_storage_account_keys_output(
      account_name=sa_backups.storage_account.name,
      resource_group_name=stack.resource_group.name,
  ).apply(lambda keys: keys.keys[0].value)
  ```

  The fix should change lines 326-330 to use `list_storage_account_keys_output` and `.apply()` to extract the key, then wrap with `pulumi.Output.secret()`:

  ```python
  account_key = storage.list_storage_account_keys_output(
      account_name=sa.storage_account.name,
      resource_group_name=self.stack.resource_group.name,
  ).apply(lambda keys: pulumi.Output.secret(keys.keys[0].value))
  ```

  Note: the test mock in `conftest.py` intercepts the `call()` for `list_storage_account_keys`, which is why the tests pass -- but the real Pulumi provider call will fail because `Output` objects cannot be serialized to plain strings for an invoke call. The mock must also be updated to verify the correct function variant is being called.

- **[components/orbitcloud_graviton/az_lib/_prefixes.py:82] Unrelated prefix rename from `"app"` to `"ca"` for `container_app` is a breaking change.**

  This change renames the resource prefix for `pulumi_azure_native.app.container_app` from `"app"` to `"ca"`. This is unrelated to the managed storage feature and will cause Pulumi to see existing container app resources as needing replacement (delete + create) on the next deployment for any stack that already has container apps. This is a destructive change that should either:
  1. Be reverted from this branch and handled as a separate, intentional migration, or
  2. At minimum be documented and acknowledged as a breaking change with a migration plan.

### Important (Should Fix)

- **[components/orbitcloud_graviton/az_app/containerapp_env.py:290] Storage account naming could produce invalid Azure names.**

  The naming pattern `f"stcae{managed.name[:8]}{self.stack.env}001"` does not validate that the resulting name meets Azure Storage Account requirements (3-24 characters, lowercase alphanumeric only). If `managed.name` contains uppercase letters, hyphens, or underscores, the generated name will be invalid and fail at deploy time. Consider adding `.lower().replace("-", "").replace("_", "")` to the name segment, or adding a Pydantic validator on `ManagedStorage.name` to enforce valid characters.

- **[components/orbitcloud_graviton/az_app/containerapp_env.py:373-393] Exports refactored to conditionally include `custom_domain_verification_id` and `dns_suffix`.**

  This is a good defensive change (avoids accessing properties on `None`), but it is also a **breaking change for existing consumers** that expect `custom_domain_verification_id` and `dns_suffix` to always be present in the exports, even as `None`. Any downstream code or Pulumi stack references that access these keys unconditionally will break. This should be documented or considered alongside a migration plan. If this is intentional and known, it should be noted in the PR description.

- **[test/components/orbitcloud_graviton/az_app/test_containerapp_env_storage.py] Missing negative/edge-case tests.**

  The requirements (P1) call for model validation tests, which are partially present, but the following gaps exist:
  - No test for `ManagedStorageFileShare` with an invalid `access_mode` value (e.g., `"Invalid"`) to verify the `Literal` type constraint rejects bad input.
  - No test for `ManagedStorage` with `extra="forbid"` -- passing an unknown field should raise a validation error.
  - No test for `ManagedStorage` with an empty `file_shares` list -- the code does not guard against this, and it would create a storage account with no file shares and no environment storages.
  - No test that verifies the storage account naming pattern (e.g., that `name[:8]` truncation works correctly).
  - No test that verifies the `storage_name` truncation to 50 characters and the underscore-to-hyphen replacement logic.

- **[test/components/orbitcloud_graviton/az_app/test_containerapp_env_storage.py:121-170] Pulumi resource tests are shallow -- they only verify list lengths, not resource properties.**

  For example, `test_storage_accounts_creates_storage` only checks `len(cae.storage_accounts) == 1` but does not verify that the storage account was created with the correct `name`, `kind`, `sku`, `hierarchical_namespace`, or `file_shares`. Similarly, `test_environment_storages_creates_resources` only checks count. The tests should use `pulumi.Output.apply()` to assert on actual resource properties (e.g., `account_name`, `share_name`, `access_mode`).

### Suggestions (Consider)

- **[components/orbitcloud_graviton/az_app/containerapp_env.py:28-41] Consider moving `ManagedStorageFileShare` and `ManagedStorage` to a dedicated types/schema file.**

  The existing pattern uses `_env_schema.py` for workload profile types. As the config models grow (storage, certificates, custom domains), the main `containerapp_env.py` file is becoming quite large. Extracting storage-related models to a `_storage_schema.py` file would improve maintainability. This is optional and can be done later.

- **[components/orbitcloud_graviton/az_app/containerapp_env.py:37] Consider validating that `file_shares` is non-empty.**

  A `ManagedStorage` with an empty `file_shares` list would create a storage account with no shares and no environment storage links -- effectively a no-op resource that incurs cost. A `@field_validator` or `@model_validator` ensuring `len(file_shares) >= 1` would prevent accidental misconfiguration.

- **[components/orbitcloud_graviton/az_app/containerapp_env.py:323] The 50-character truncation on `storage_name` could silently produce collisions.**

  If two different share names produce the same first 50 characters after transformation, they would collide. Consider raising an error or warning if truncation occurs.

### Praise

- Good reuse of the existing `StorageAccount` component and `StorageAccountConfig` / `StorageAccountFileShareConfig` models, rather than reimplementing storage account creation from scratch. This keeps the codebase DRY.
- The subnet merging logic in `_storage_accounts()` (combining CAE subnet with storage-specific subnets) is clean and well-commented.
- All non-versioned Pulumi Azure Native imports are used correctly (`from pulumi_azure_native import app, dns, monitor, storage`), exactly as required by the project conventions.
- The Pydantic models correctly use `ConfigDict(extra="forbid")` and `Literal` types, consistent with project patterns.
- Storage account keys are correctly wrapped with `pulumi.Output.secret()` to prevent them from appearing in plaintext in state files and logs.
- The test conftest properly mocks `list_storage_account_keys` via `call()`, showing awareness of the Pulumi testing patterns.
- The `tags` support on `ContainerAppEnvConfig` is a nice addition that was cleanly implemented.

## Summary

**Verdict: REQUEST CHANGES**

The implementation closely follows the requirements and demonstrates good understanding of the codebase patterns. However, there is one critical bug that will cause runtime failures:

1. **Critical**: `storage.list_storage_account_keys()` is called with `Output[str]` arguments. Must switch to `list_storage_account_keys_output()` to match the existing pattern in `oradb_base.py`.

2. **Critical**: The `_prefixes.py` change (`"app"` -> `"ca"`) is an unrelated breaking change that will cause resource replacement on existing deployments.

Additionally, the tests need to be deepened: they currently verify resource creation counts but not the correctness of resource properties, which is the more valuable assertion.

**Estimated effort to address feedback**: 1-2 hours.
- Fix `list_storage_account_keys` -> `list_storage_account_keys_output`: ~15 minutes
- Revert or separate the prefixes change: ~5 minutes
- Add negative/edge-case tests and deepen property assertions: ~1 hour
- Storage account name validation: ~15 minutes

## Developer Response

All findings have been addressed. Details below:

### Critical Fixes

1. **`list_storage_account_keys` -> `list_storage_account_keys_output`**: Fixed in `containerapp_env.py:326-330`. Now uses `storage.list_storage_account_keys_output()` with `.apply()` to extract the key and wrap with `pulumi.Output.secret()`, matching the pattern in `oradb_base.py:68`.

2. **`_prefixes.py` reverted**: Used `git checkout main -- components/orbitcloud_graviton/az_lib/_prefixes.py` to restore the original `"app"` prefix for `container_app`. The `"ca"` rename should be handled as a separate, intentional migration.

### Important Fixes

3. **Storage account name sanitization**: Added sanitization logic that strips non-alphanumeric characters and lowercases the name segment before building the storage account name. This ensures compliance with Azure Storage Account naming requirements (lowercase alphanumeric only).

4. **`_outputs()` method reverted**: Restored the original unconditional export of `custom_domain_verification_id` and `dns_suffix` to avoid breaking downstream consumers. Updated the conftest mock to provide `customDomainConfiguration` with mock values so tests pass when no custom domain is configured.

5. **Enhanced tests**: Added 14 new tests (total now 74, up from 60):
   - Edge case: invalid `access_mode` rejected by Literal constraint
   - Edge case: `extra="forbid"` rejects unknown fields on both models
   - Edge case: empty `file_shares` list behavior
   - Storage account naming: truncation, uppercase, hyphens, underscores
   - Environment storage naming: underscore-to-hyphen, 50-char truncation
   - Resource property verification: config properties (name, kind, sku, etc.)
   - Resource URN verification for environment storages
   - Multiple managed storages test
   - Access mode test with 3 shares

### Suggestions (Not Addressed)

- Moving models to `_storage_schema.py`: Deferred as optional, per review.
- Validating non-empty `file_shares`: Deferred; added a test documenting the current behavior.
- 50-char truncation collision warning: Deferred; unlikely in practice.

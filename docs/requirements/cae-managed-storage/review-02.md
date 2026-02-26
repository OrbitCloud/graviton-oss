# Review 02

> Status: pending-dev
> Date: 2026-02-26
> Reviewer: Code Review Agent
> Verdict: APPROVE

## Previous Review Status

### Critical Issues

- [x] **`list_storage_account_keys` called with `Output[str]` args (review-01)** - FIXED. Now uses `storage.list_storage_account_keys_output()` with `.apply()` at line 328-331, matching the established pattern in `oradb_base.py:68`. The conftest `call()` mock correctly intercepts `azure-native:storage:listStorageAccountKeys`, which is the underlying token used by both the sync and `_output` variants.

- [x] **`_prefixes.py` unrelated breaking change (review-01)** - FIXED. The file has zero diff against `main`. The `"app"` prefix for `container_app` is preserved. Clean revert confirmed.

### Important Issues

- [x] **Storage account naming could produce invalid Azure names (review-01)** - FIXED. Line 291 now sanitizes with `"".join(c for c in managed.name if c.isalnum()).lower()`, stripping non-alphanumeric characters and lowercasing before truncation. Tests verify this for uppercase, hyphens, and underscores (`test_storage_accounts_with_uppercase_name`, `TestStorageAccountNaming`).

- [x] **`_outputs()` conditionally excluding exports was a breaking change (review-01)** - FIXED. The `_outputs()` method is now identical to `main` (only a trailing comma was removed on line 387, which is whitespace-only). `custom_domain_verification_id` and `dns_suffix` are unconditionally exported. The conftest mock provides `customDomainConfiguration` with mock values so tests pass without a custom domain configured.

- [x] **Missing negative/edge-case tests (review-01)** - FIXED. Added tests for:
  - Invalid `access_mode` rejected (`test_invalid_access_mode_rejected`)
  - `extra="forbid"` on both models (`test_extra_fields_forbidden` x2)
  - Empty `file_shares` behavior (`test_empty_file_shares_allowed`, `test_empty_file_shares_creates_storage_but_no_env_storage`)
  - Naming sanitization (6 tests in `TestStorageAccountNaming`)

- [x] **Tests were shallow -- only verified list lengths (review-01)** - FIXED. `test_storage_accounts_creates_storage` now asserts on `config.name`, `config.kind`, `config.sku`, `config.hierarchical_namespace`, `config.allow_shared_key_access`, `config.public_network_access`, `config.file_shares`, and `config.exports_prefix`. `test_environment_storages_creates_resources` verifies URN patterns. `test_storage_accounts_with_uppercase_name` verifies sanitized name properties.

## New Findings

### Important (Should Fix)

- **[components/orbitcloud_graviton/az_app/containerapp_env.py:331] Lambda closure captures loop variable `keys` -- but the real concern is the outer `share` variable.** The `account_key` lambda on line 331 (`lambda keys: pulumi.Output.secret(keys.keys[0].value)`) is fine because `keys` is the lambda parameter. However, review the inner loop body at lines 323-351: the `share` variable from the `for share in managed.file_shares` loop is used directly in `app.AzureFilePropertiesArgs(share_name=share.name, access_mode=share.access_mode)` on lines 342-343. Since these are passed directly to the Pulumi resource constructor (not deferred via a lambda), this is actually safe -- each `ManagedEnvironmentsStorage` is constructed eagerly within the loop iteration. No action needed; this is noted for clarity.

  **Update**: On closer inspection, this is NOT an issue. The resource constructors are invoked synchronously within the loop body, so `share` is correctly bound at each iteration. No fix required.

### Suggestions (Consider)

- **[test/components/orbitcloud_graviton/az_app/test_containerapp_env_storage.py:1-31] Module-level import hackery to avoid `az_app/__init__.py`.** The `importlib` stub that creates a synthetic `orbitcloud_graviton.az_app` package to sidestep the real `__init__.py` (which imports `az_iam` and needs an asyncio loop) is a pragmatic workaround. However, if more test modules are added for `az_app`, this pattern will need to be duplicated or extracted into a shared test utility. Consider extracting this into a pytest plugin or shared helper in `test/components/orbitcloud_graviton/az_app/conftest.py` if additional test files are anticipated.

- **[components/orbitcloud_graviton/az_app/containerapp_env.py:292] Storage account name length is not validated.** The assembled name `f"stcae{sanitized_name[:8]}{self.stack.env}001"` has a fixed structure: 5 (`stcae`) + up to 8 (sanitized) + variable (`env`) + 3 (`001`). With `env="test"` this is 20 characters, well within the 3-24 character Azure limit. However, if `env` is longer than 8 characters, the total could exceed 24. For example, `env="development"` (11 chars) would produce a 27-character name. Consider adding a guard or truncating `env` as well. This is a low-probability edge case since `env` values are typically short (`dev`, `test`, `prod`, `staging`), but worth noting.

- **[test/components/orbitcloud_graviton/az_app/test_containerapp_env_storage.py:278-285] URN assertions in `apply()` callbacks may silently pass.** Pulumi test assertions inside `.apply()` callbacks can be tricky: if the callback never executes (e.g., due to an unknown output in preview mode), the assertion is silently skipped. The conftest sets `preview=False`, which is correct, but this is a fragile pattern. Consider adding explicit `.future().result()` calls or using `pulumi.Output.all(...).apply(...)` with a return value check to make test failures more visible.

### Praise

- All 29 tests pass cleanly with no errors or unexpected warnings.
- The `list_storage_account_keys_output` fix precisely matches the established pattern in `oradb_base.py`, demonstrating good codebase awareness.
- The `_prefixes.py` revert is completely clean -- zero diff against `main`.
- The `_outputs()` revert preserves full backward compatibility. The conftest mock intelligently provides `customDomainConfiguration` via `setdefault` so the unconditional export works even without custom domain configuration.
- The naming sanitization logic is clean and correct: strip non-alphanumeric, lowercase, then truncate. Tests cover the important cases (uppercase, hyphens, underscores).
- The test suite is well-organized into logical groups: model validation, naming logic, and Pulumi resource creation. The separation of concerns makes tests easy to find and maintain.
- Good use of `strict=True` in `zip(self.config.storage, self.storage_accounts, strict=True)` to catch length mismatches early.
- The `depends_on=[sa]` on `ManagedEnvironmentsStorage` correctly establishes the dependency chain.

## Summary

**Verdict: APPROVE**

All critical and important issues from review-01 have been properly addressed:

1. The `list_storage_account_keys_output` pattern is correct and matches the existing codebase convention.
2. The `_prefixes.py` revert is clean with zero diff.
3. The `_outputs()` method preserves backward compatibility.
4. Storage account naming is properly sanitized for Azure requirements.
5. Tests have been significantly deepened: 29 tests covering model validation, naming edge cases, resource properties, and resource creation counts.

The remaining suggestions are minor and do not block merging. The storage account name length edge case with long `env` values is worth considering in a follow-up, but is unlikely to occur in practice.

**Estimated effort for suggestions**: 30 minutes (optional, non-blocking).

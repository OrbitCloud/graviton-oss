# Review 01

> Status: pending-dev
> Date: 2026-02-28
> Reviewer: Code Review Agent
> Verdict: APPROVE

## Previous Review Status

No previous reviews.

## New Findings

### Critical (Must Fix)

None.

### Important (Should Fix)

None.

### Suggestions (Consider)

- **[bases/orbitcloud_graviton/app_zone/app_zone_base.py:48]** The duplicate detection uses `names.count(n)` inside a set comprehension, which is O(n^2). For the expected list sizes (single-digit storage accounts) this is perfectly fine, but a more idiomatic approach would use a single pass with a `set`:

  ```python
  seen: set[str] = set()
  duplicates: set[str] = set()
  for sa in self.storage_accounts:
      if sa.name in seen:
          duplicates.add(sa.name)
      seen.add(sa.name)
  ```

  This is purely a style suggestion -- the current implementation is correct and readable.

- **[bases/orbitcloud_graviton/app_zone/app_zone_base.py:45]** The return type annotation uses the string literal `"AppZoneBaseConfig"` for forward reference. Since this is Python 3.13+ and the class is already fully defined by the time the validator runs, the bare class name `AppZoneBaseConfig` (without quotes) would also work. However, the quoted form is harmless and sometimes preferred for consistency with `from __future__ import annotations` style. No action needed.

- **[test/bases/orbitcloud_graviton/app_zone/test_app_zone_config.py:14-35]** The `az_iam` module stubbing is a pragmatic workaround, but it is fairly verbose. If more base tests are added in the future, consider extracting this into a shared `conftest.py` inside `test/bases/` to keep individual test files focused. Not necessary for this PR.

### Praise

- Clean, focused changes. The diff is minimal and each change directly addresses a specific requirement.
- Good use of `@model_validator(mode="after")` on `AppZoneBaseConfig` -- this is the correct Pydantic v2 pattern for cross-field validation and catches duplicates at config load time before Pulumi ever starts provisioning.
- The `_minimal_config` helper in `test_storage_account.py` with internet routing to avoid the `microsoft_endpoints` code path is a thoughtful workaround that keeps tests fast and independent.
- The `patch.object(StorageAccount, "_outputs")` approach in resource naming tests is pragmatic -- it isolates the URN verification from the export logic that depends on mock-incompatible Pulumi output properties.
- Test coverage is thorough: 5 config validation tests + 5 app zone config tests + 2 resource naming tests cover all acceptance criteria including edge cases (None, empty list, single account, duplicates, name omission).
- The existing caller in `containerapp_env.py` already provides `name`, so the breaking change has no impact on internal code.

## Summary

- **Overall assessment:** APPROVE
- **Key concerns:** None. The implementation is correct, well-tested, and minimal.
- **Estimated effort to address suggestions:** ~5 minutes (all optional)

All three tasks from the requirements are fully implemented:
1. `StorageAccountConfig.name` is now a required `str` field (Task 01)
2. The Pulumi `ComponentResource` name uses `f"st-{self.config.name}"` instead of the hardcoded workload name (Task 02)
3. `AppZoneBaseConfig` rejects duplicate storage account names via a model validator (Task 03)

All 615 tests pass (4 skipped), including the 10 new tests added by this branch. The code follows existing project patterns and Pydantic v2 conventions.

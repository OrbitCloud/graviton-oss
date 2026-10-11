# Task 03: Add duplicate name validator to AppZoneBaseConfig

> Status: done

## Goal
Add a Pydantic validator on `AppZoneBaseConfig.storage_accounts` that rejects duplicate `name` values within the list.

## Acceptance Criteria
- [ ] Duplicate `name` values in `storage_accounts` raise `ValidationError`
- [ ] Unique names pass validation
- [ ] `None` (no storage accounts) passes validation
- [ ] Tests verify all cases

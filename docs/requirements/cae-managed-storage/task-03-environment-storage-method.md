# Task 03: Implement _environment_storage() Method

> Status: done

## Goal
Implement the `_environment_storage()` method that creates `app.ManagedEnvironmentsStorage` resources linking file shares to the Container App Environment.

## Acceptance Criteria
- [x] Returns `None` if `config.storage` is not set
- [x] Creates `ManagedEnvironmentsStorage` for each storage + file share pair
- [x] Uses `storage.list_storage_account_keys()` to retrieve keys as secrets
- [x] Storage name format: `{storage_name}-{share_name}` lowercased, underscores to hyphens, max 50 chars
- [x] Parents under `self.environment` with `depends_on=[storage_account]`
- [x] Wired into `__init__` after `self.storage_accounts`
- [x] Tests pass

## Notes

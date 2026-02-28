# Task 01: Make StorageAccountConfig.name a required field

> Status: done

## Goal
Change `StorageAccountConfig.name` from `str | None = None` to `str` so that omitting `name` produces a Pydantic validation error.

## Acceptance Criteria
- [ ] `StorageAccountConfig.name` is `str` (required, no default)
- [ ] Omitting `name` raises `ValidationError`
- [ ] Providing a name still works as before
- [ ] Tests verify both cases

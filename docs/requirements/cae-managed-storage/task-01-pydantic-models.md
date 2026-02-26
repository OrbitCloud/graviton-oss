# Task 01: Add Pydantic Models for Managed Storage

> Status: done

## Goal
Create the `ManagedStorageFileShare` and `ManagedStorage` Pydantic models, and add the `storage` and `tags` fields to `ContainerAppEnvConfig`.

## Acceptance Criteria
- [x] `ManagedStorageFileShare` model with `name` and `access_mode` fields
- [x] `ManagedStorage` model with `name`, `file_shares`, `sku`, `allowed_private_subnets` fields
- [x] `storage` field added to `ContainerAppEnvConfig`
- [x] `tags` field added to `ContainerAppEnvConfig`
- [x] Tests for model validation pass

## Notes

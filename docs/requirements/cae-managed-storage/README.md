# CAE Managed Storage Requirements

## Overview
Add managed storage support to the `ContainerAppEnv` component, allowing Azure Storage Account file shares to be mounted as volumes in Container App Environments.

## Goals
- Enable users to attach Azure File Shares to Container App Environments
- Automatically provision Storage Accounts and link them as environment storage
- Support access mode control (ReadOnly/ReadWrite) per file share
- Support subnet-based network restrictions on storage accounts

## Reference Implementation
The reference implementation is from a gist that uses **versioned SDK imports** (`v20241002preview`, `v20230501`).
**IMPORTANT**: This project uses **non-versioned** Pulumi Azure Native imports. All imports must use the standard pattern:
```python
from pulumi_azure_native import app, storage
```
NOT versioned like:
```python
from pulumi_azure_native.app import v20241002preview as app  # WRONG
```

## Functional Requirements

### Must Have (P0)

- [ ] New `ManagedStorageFileShare` Pydantic model with:
  - `name: str` - file share name
  - `access_mode: Literal["ReadOnly", "ReadWrite"] | None = None` - access mode

- [ ] New `ManagedStorage` Pydantic model with:
  - `name: str` - storage identifier name
  - `file_shares: list[ManagedStorageFileShare]` - list of file shares to create
  - `sku: storage.SkuName = storage.SkuName.STANDARD_ZRS` - storage SKU
  - `allowed_private_subnets: list[AzureIdRef] | None = None` - additional subnet restrictions
  - `model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")`

- [ ] Add `storage: list[ManagedStorage] | None = None` field to `ContainerAppEnvConfig`

- [ ] Add `tags: dict[str, StrRef | str] | None = None` field to `ContainerAppEnvConfig` and pass to ManagedEnvironment

- [ ] New `_storage_accounts()` method on `ContainerAppEnv` that:
  - Returns `None` if `config.storage` is not set
  - For each `ManagedStorage` entry, creates a `StorageAccount` using the existing `az_storage.StorageAccount` component
  - Combines the CAE subnet_id with any `allowed_private_subnets` from the storage config
  - Uses naming pattern: `stcae{name[:8]}{env}001`
  - Sets `kind=storage.Kind.STORAGE_V2`, `hierarchical_namespace=True`, `allow_shared_key_access=True`
  - Sets `public_network_access=storage.PublicNetworkAccess.ENABLED`
  - Creates file shares via `StorageAccountFileShareConfig`
  - Sets `exports_prefix` for namespaced outputs
  - Parents the storage account under `self.environment`

- [ ] New `_environment_storage()` method on `ContainerAppEnv` that:
  - Returns `None` if `config.storage` is not set
  - For each storage + file share pair, creates `app.ManagedEnvironmentsStorage`
  - Uses `storage.list_storage_account_keys()` to retrieve the primary key (as a secret)
  - Links the file share to the environment with correct access mode
  - Storage name format: `{storage_name}-{share_name}` lowercased, underscores to hyphens, max 50 chars
  - Parents under `self.environment` with `depends_on=[storage_account]`

- [ ] Wire `_storage_accounts()` and `_environment_storage()` into `__init__`:
  - `self.storage_accounts` after `self.certificates`
  - `self.environment_storages` after `self.storage_accounts`

### Should Have (P1)
- [ ] Tests for `ManagedStorageFileShare` model validation
- [ ] Tests for `ManagedStorage` model validation
- [ ] Tests for `ContainerAppEnvConfig` with storage field
- [ ] Tests for `_storage_accounts()` method creating correct resources
- [ ] Tests for `_environment_storage()` method creating correct resources

## Non-Functional Requirements
- **Backwards Compatibility**: The `storage` field defaults to `None`, so existing configs remain valid
- **Security**: Storage account keys are marked as Pulumi secrets via `pulumi.Output.secret()`
- **Naming**: Follow existing resource naming conventions

## Affected Components
- `components/orbitcloud_graviton/az_app/containerapp_env.py` - Main changes
- `test/` - New tests for the storage functionality

## Dependencies
- `orbitcloud_graviton.az_storage.StorageAccount` - Existing component for creating storage accounts
- `pulumi_azure_native.app.ManagedEnvironmentsStorage` - Azure resource for linking storage
- `pulumi_azure_native.storage.list_storage_account_keys` - For retrieving storage keys

## Out of Scope
- NFS storage type support (the `type` field from the gist is not used in the implementation)
- Changes to `_env_schema.py`
- Changes to `__init__.py` exports (no new public types needed beyond config models)

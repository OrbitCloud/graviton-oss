# Task 02: Implement _storage_accounts() Method

> Status: done

## Goal
Implement the `_storage_accounts()` method on `ContainerAppEnv` that creates `StorageAccount` instances for each `ManagedStorage` entry.

## Acceptance Criteria
- [x] Returns `None` if `config.storage` is not set
- [x] Creates `StorageAccount` for each `ManagedStorage` entry
- [x] Uses naming pattern `stcae{name[:8]}{env}001`
- [x] Combines CAE subnet_id with storage allowed_private_subnets
- [x] Sets correct defaults (kind, hierarchical_namespace, allow_shared_key_access, public_network_access)
- [x] Creates file shares via `StorageAccountFileShareConfig`
- [x] Wired into `__init__` after `self.certificates`
- [x] Tests pass

## Notes

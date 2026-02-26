# ContainerApp Volume Mount Support - Summary

## What Was Implemented

### New Pydantic Models

Two new configuration models were added to `container_app.py`:

- **`VolumeMountConfig`** - Defines a volume mount on a container with fields:
  - `volume_name: str` - must match a volume name
  - `mount_path: str` - absolute path inside the container
  - `sub_path: str | None = None` - optional subdirectory within the volume
  - Uses `ConfigDict(extra="forbid")`

- **`VolumeConfig`** - Defines a volume in the app template with fields:
  - `name: str` - volume identifier
  - `storage_name: str` - reference to ManagedEnvironmentsStorage
  - `storage_type: app.StorageType = app.StorageType.AZURE_FILE` - defaults to AzureFile
  - `mount_options: str | None = None` - comma-separated mount options
  - Uses `ConfigDict(arbitrary_types_allowed=True, extra="forbid")`

### Updated Existing Models

- **`ContainerConfig`** - Added `volume_mounts: list[VolumeMountConfig] | None = None`
- **`ContainerAppBaseConfig`** - Added `volumes: list[VolumeConfig] | None = None`

### Updated Methods

- **`_containers()`** - Now delegates to `_volume_mounts()` helper which merges secret volume mounts with per-container Azure File volume mounts
- **`_app_template()`** - Now delegates to `_volumes()` helper which merges secret volumes with Azure File volumes
- Both return `None` when no volumes are configured (preserving backwards compatibility)

### New Helper Methods

- **`_volume_mounts(container)`** - Builds combined list: secret mount (if secrets with filenames) + container-specific Azure File mounts
- **`_volumes()`** - Builds combined list: secret volume (if secrets with filenames) + config.volumes mapped to `VolumeArgs`

## Tests Added

23 tests in `/Users/on/src/graviton-oss/test/components/orbitcloud_graviton/az_app/test_container_app_volumes.py`:

- **TestVolumeMountConfig** (3 tests) - minimal, sub_path, extra fields forbidden
- **TestVolumeConfig** (5 tests) - minimal/defaults, NFS, SMB, mount_options, extra fields forbidden
- **TestContainerConfigVolumeMounts** (3 tests) - defaults to None, with mounts, empty list
- **TestContainerAppBaseConfigVolumes** (2 tests) - defaults to None, with volumes
- **TestVolumeMergeInContainers** (5 tests) - no volumes, Azure File only, coexistence with secrets, sub_path passthrough, multiple containers with independent mounts
- **TestVolumeMergeInAppTemplate** (5 tests) - no volumes, Azure File only, coexistence with secrets, multiple volumes, mount_options passthrough

## Decisions and Trade-offs

1. **Test isolation**: The `container_app.py` module has deep import chains (`az_iam` requires an async event loop at import time). Tests use `importlib` with temporary module stubs that are cleaned up after loading, preventing pollution of other test modules.

2. **Helper construction in tests**: Integration tests use `_make_container_app()` which constructs a `ContainerApp` via `__new__` and sets attributes directly, bypassing `__init__` (which creates real Pulumi resources). This keeps tests fast and focused on the merge logic.

3. **Secret volumes first**: When both secret and Azure File volumes coexist, secret volumes/mounts appear first in the list. This matches the existing convention and keeps the secret mount behavior stable.

4. **Empty list returns None**: Both `_volume_mounts()` and `_volumes()` return an empty list when no volumes are configured, which is then converted to `None` via `or None`. This preserves the existing API behavior.

## Validation Results

- `make fmt` - All files formatted
- `make lint` - All checks passed
- `make test` - 102 tests passed (23 new + 79 existing)

## Files Changed

- `/Users/on/src/graviton-oss/components/orbitcloud_graviton/az_app/container_app.py` - Added models, fields, and merge logic
- `/Users/on/src/graviton-oss/test/components/orbitcloud_graviton/az_app/test_container_app_volumes.py` - New test file

## Suggested Next Steps

- Export `VolumeMountConfig` and `VolumeConfig` from `az_app/__init__.py` if they should be part of the public API
- Add job volume support if `_job_template()` gains a `volumes` parameter in the Pulumi SDK
- Consider validation that `volume_mount.volume_name` references a defined volume name (currently deferred to Azure API)

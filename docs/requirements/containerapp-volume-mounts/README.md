# ContainerApp Volume Mount Support

## Overview
Add Azure File volume mount support to the `ContainerApp` component so containers can mount file shares provisioned by `ContainerAppEnv` managed storage. Currently only secret volume mounts are supported.

## Goals
- Enable users to mount Azure File shares into container app containers via YAML config
- Support all Azure storage types: AzureFile, NfsAzureFile, SMB
- Coexist cleanly with existing secret volume mount functionality
- Full backwards compatibility — no volumes configured = existing behavior unchanged

## User Stories
As a platform engineer, I want to define volume mounts in my container app YAML config so that my containers can access persistent Azure File shares provisioned by the environment.

## Target YAML Config

Volumes are defined at the app level, volume_mounts on each container:

```yaml
apps:
  - name: my-app
    # ... existing config ...
    volumes:
      - name: app-data
        storage_name: myapp-app-data   # matches ManagedEnvironmentsStorage name
        storage_type: AzureFile        # or NfsAzureFile, SMB
      - name: app-files
        storage_name: myapp-app-files
        storage_type: AzureFile
    containers:
      - name: app
        image: myregistry/app:latest
        volume_mounts:
          - volume_name: app-data
            mount_path: /app/data
          - volume_name: app-files
            mount_path: /app/files
```

## Functional Requirements

### Must Have (P0)

- [ ] New `VolumeMountConfig` Pydantic model with:
  - `volume_name: str` — must match a volume name
  - `mount_path: str` — absolute path inside the container
  - `sub_path: str | None = None` — optional subdirectory within the volume
  - `model_config = ConfigDict(extra="forbid")`

- [ ] New `VolumeConfig` Pydantic model with:
  - `name: str` — volume identifier
  - `storage_name: str` — reference to `ManagedEnvironmentsStorage` storage_name
  - `storage_type: app.StorageType = app.StorageType.AZURE_FILE` — default to AzureFile
  - `mount_options: str | None = None` — comma-separated mount options
  - `model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")`

- [ ] Add `volume_mounts: list[VolumeMountConfig] | None = None` field to `ContainerConfig`

- [ ] Add `volumes: list[VolumeConfig] | None = None` field to `ContainerAppBaseConfig`

- [ ] Update `_containers()` method to merge secret volume mounts with Azure File volume mounts:
  - Build combined list: secret mount (if secrets with filenames) + per-container volume_mounts
  - Map each `VolumeMountConfig` to `app.VolumeMountArgs(volume_name, mount_path, sub_path)`
  - Pass combined list or `None` if empty

- [ ] Update `_app_template()` method to merge secret volumes with Azure File volumes:
  - Build combined list: secret volume (if secrets with filenames) + config.volumes
  - Map each `VolumeConfig` to `app.VolumeArgs(name, storage_name, storage_type, mount_options)`
  - Pass combined list or `None` if empty

### Should Have (P1)

- [ ] Tests for `VolumeMountConfig` model validation (defaults, extra="forbid")
- [ ] Tests for `VolumeConfig` model validation (defaults to AZURE_FILE, extra="forbid")
- [ ] Tests for `ContainerConfig` with volume_mounts field
- [ ] Tests for `ContainerAppConfig` with volumes field
- [ ] Tests for volume + volume_mount coexistence with secret volumes
- [ ] Tests for no volumes configured = existing behavior unchanged

## Non-Functional Requirements
- **Backwards Compatibility**: Both new fields default to `None`, so existing configs remain valid
- **Security**: No sensitive data in volume config (keys are handled at environment storage level)

## Edge Cases & Error Handling
| Scenario | Expected Behavior |
|----------|-------------------|
| No volumes or volume_mounts configured | Existing behavior unchanged (secret mounts only) |
| Volumes defined but no containers reference them | Volumes created in template, no mounts — valid Azure config |
| volume_mount references non-existent volume name | Azure API will reject at deploy time (not validated by us) |
| Both secret files and Azure File volumes configured | Both coexist in the volumes/volume_mounts lists |
| Jobs with volumes | Jobs use `_containers()` so volume_mounts work, but `_job_template()` does not have volumes param — out of scope |

## Affected Components
- `components/orbitcloud_graviton/az_app/container_app.py` — main changes (models + methods)
- `test/components/orbitcloud_graviton/az_app/` — new tests

## Out of Scope
- Job volume support (`_job_template()` doesn't have a `volumes` parameter)
- Validation that volume_name references match defined volumes (Azure handles this)
- EmptyDir volume type support

## Dependencies
- `pulumi_azure_native.app.VolumeArgs` — SDK type for volume definitions
- `pulumi_azure_native.app.VolumeMountArgs` — SDK type for container volume mounts
- `pulumi_azure_native.app.StorageType` — enum (AZURE_FILE, NFS_AZURE_FILE, SMB, SECRET)
- CAE managed storage feature (already implemented on this branch)

## Acceptance Criteria
- `make fmt && make lint && make test` passes
- Existing container app tests still pass
- New models accept the target YAML config structure
- Azure File volumes and secret volumes coexist correctly in template output

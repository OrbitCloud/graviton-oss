# Task 01: Pydantic Config Models for Volume Mounts

> Status: done

## Goal
Create VolumeMountConfig and VolumeConfig Pydantic models, and add volume fields to ContainerConfig and ContainerAppBaseConfig.

## Acceptance Criteria
- [x] VolumeMountConfig with volume_name, mount_path, sub_path fields
- [x] VolumeConfig with name, storage_name, storage_type, mount_options fields
- [x] ContainerConfig has volume_mounts field (optional)
- [x] ContainerAppBaseConfig has volumes field (optional)
- [x] Tests for all model validations

## Notes
Models must use ConfigDict(extra="forbid") per project conventions.

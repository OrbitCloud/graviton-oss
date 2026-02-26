# Task 02: Merge Volume Logic in _containers() and _app_template()

> Status: done

## Goal
Update _containers() and _app_template() to merge secret volumes with Azure File volumes.

## Acceptance Criteria
- [x] _containers() merges secret volume mounts with per-container volume_mounts
- [x] _app_template() merges secret volumes with config.volumes
- [x] No volumes configured = existing behavior unchanged
- [x] Both secret and Azure File volumes coexist correctly
- [x] Tests for all merge scenarios

## Notes
Must maintain backwards compatibility. None when no volumes at all.

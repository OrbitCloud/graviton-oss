# Task 03: Exports and AppWorkload Wiring

> Status: done

## Goal
Export new types from az_app __init__.py and wire http_routes into AppWorkloadConfig and deploy().

## Acceptance Criteria
- [ ] Export HttpRouteConfigModel from az_app __init__.py
- [ ] Add http_routes field to AppWorkloadConfig
- [ ] Wire into deploy() function after container apps are created
- [ ] No-op when http_routes is None

## Notes
Route configs need environment_name and resource_group_name from environment output ref.

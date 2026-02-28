# Task 02: Builder Function for HttpRouteConfig Pulumi Resource

> Status: done

## Goal
Create `build_http_route_config()` builder function that creates `app.HttpRouteConfig` Pulumi resources.

## Acceptance Criteria
- [ ] Builder takes environment_name, resource_group_name, config, and opts
- [ ] Creates app.HttpRouteConfig with correct args mapping
- [ ] Returns the created resource
- [ ] Reuses CustomDomainConfig from ingress module for custom_domains

## Notes
Follow the pattern from resiliency.py `app_resiliency()` function.

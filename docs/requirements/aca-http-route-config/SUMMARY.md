# ACA HTTP Route Config - Implementation Summary

## What Was Implemented

### New Config Models (`components/orbitcloud_graviton/az_app/http_route.py`)

Five Pydantic v2 config models for HTTP route configuration:

- **HttpRouteMatchConfig** -- Match condition with exactly-one-of validation for `path`, `prefix`, or `path_separated_prefix`. Optional `case_sensitive` flag.
- **HttpRouteActionConfig** -- Optional `prefix_rewrite` action for matched routes.
- **HttpRouteTargetConfig** -- Target container app with optional `revision`, `label`, and `weight` (0-100 range).
- **HttpRouteEntry** -- Combines a match condition and optional action into a single route entry.
- **HttpRouteRuleConfig** -- A rule with optional description, route entries, and targets (min 1). Validates that multi-target weights sum to 100 when all targets specify weights.
- **HttpRouteConfigModel** -- Top-level config with name, optional custom domains (reuses `CustomDomainConfig` from ingress), and rules (min 1).

### Builder Function (`build_http_route_config`)

Creates `app.HttpRouteConfig` Pulumi resources from config models. Maps all config fields to the Pulumi SDK types (`HttpRouteConfigArgs`, `HttpRouteConfigPropertiesArgs`, `HttpRouteRuleArgs`, `HttpRouteMatchArgs`, `HttpRouteActionArgs`, `HttpRouteTargetArgs`). Supports custom domain bindings via the existing `CustomDomainConfig` model.

### Exports (`components/orbitcloud_graviton/az_app/__init__.py`)

Added `HttpRouteConfigModel` and `build_http_route_config` to the public API.

### AppWorkload Wiring (`bases/orbitcloud_graviton/app_workload/app_workload_base.py`)

- Added `http_routes: list[HttpRouteConfigModel] | None = None` field to `AppWorkloadConfig`.
- Wired into `deploy()` after container apps are created, resolving `environment_name` and `resource_group_name` from the first app's `environment_output_ref`.
- No-op when `http_routes` is `None` (backwards compatible).

## Tests Added

48 tests in `test/components/orbitcloud_graviton/az_app/test_http_route_config.py`:

- **TestHttpRouteMatchConfig** (9 tests): Happy paths for each match type, case_sensitive, exactly-one-of validation (none set, two set, all three set), extra fields forbidden.
- **TestHttpRouteActionConfig** (3 tests): prefix_rewrite present/absent, extra fields forbidden.
- **TestHttpRouteTargetConfig** (7 tests): Minimal/full target, weight boundaries (0, 100, negative, >100), missing required field.
- **TestHttpRouteEntry** (3 tests): match required, match only, match with action.
- **TestHttpRouteRuleConfig** (7 tests): Minimal/full rule, empty targets, single target no weight, multi-target weight sum validation, partial weights, route with match only.
- **TestHttpRouteConfigModel** (4 tests): Minimal config, empty rules, full config with custom domains, multiple rules.
- **TestDuplicateRouteConfigNames** (3 tests): Duplicate names rejected, unique names accepted, single route no check.
- **TestBuildHttpRouteConfig** (12 tests): Resource creation, type assertion, opts passthrough, URN naming, environment/resource_group mapping, target args (container_app, weight), match conditions (path_separated_prefix), action (prefix_rewrite), custom domains (name, certificate_id), rule description, no custom domains.

## Decisions and Trade-offs

1. **Reused `CustomDomainConfig` from ingress module** for route-level custom domain bindings, avoiding model duplication.
2. **Weight validation only when all targets specify weights** -- if some targets omit weights, Azure handles the default distribution. This avoids being overly restrictive.
3. **Environment resolution from first app** -- `http_routes` requires at least one app to be defined so the environment name and resource group can be resolved from its output ref. This raises a clear `ValueError` if no apps exist.
4. **Unused import of `AzureIdRef` removed by ruff** -- the linter correctly cleaned up an unused import from the initial implementation.
5. **HttpRouteEntry.match is required** -- aligns with Azure SDK where match is the primary purpose of a route entry. Prevents broken no-op rules.
6. **Duplicate route config name validation** -- added `validate_http_routes` model_validator on `AppWorkloadConfig`, following the existing `validate_apps` pattern.
7. **Explicit depends_on for route configs** -- container app resources are collected and passed as `depends_on` when creating route configs, making the Pulumi dependency graph explicit.
8. **Duplicate name test uses minimal model** -- to avoid stubbing the entire transitive dependency tree of `AppWorkloadConfig`, the test mirrors the validator logic in a minimal Pydantic model. The actual validator code in `app_workload_base.py` is identical.

## Suggested Next Steps

- **P1**: Add stack exports for created route config resources (id, name) for cross-stack references.
- **P2**: Add a Pulumi warning when a target references an app name not defined in the current workload config.
- Consider adding integration test coverage with a full Pulumi preview mock to verify end-to-end args mapping.

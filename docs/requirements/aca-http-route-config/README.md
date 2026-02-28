# ACA HTTP Route Config Requirements

## Overview

Add support for Azure Container Apps `HttpRouteConfig` — an environment-level resource that enables
path-based and prefix-based HTTP traffic routing across container apps within a managed environment.
This allows users to split traffic based on route matching rules, direct requests to specific apps
or revisions with weighted distribution, and optionally bind custom domains to routes.

## Goals

- Enable path/prefix-based HTTP routing across container apps in the same environment
- Support weighted traffic splitting to different apps, revisions, or labels (canary, blue-green)
- Support custom domain bindings on route configs
- Support prefix rewrite actions
- Allow referencing container apps from the same workload or from other workload stacks

## User Stories

As a platform engineer, I want to define HTTP route rules on my container app environment so that
incoming requests are routed to different container apps based on URL path matching.

As a platform engineer, I want to split traffic by weight across revisions or apps so that I can
perform canary deployments and A/B testing.

As a platform engineer, I want to bind custom domains to route configs so that different routes
can serve traffic for specific domains.

As a platform engineer, I want to reference container apps from other workload stacks as route
targets so that I can compose routing across independently deployed services.

## Functional Requirements

### Must Have (P0)

- [ ] New Pydantic config models for HTTP route configuration:
  - `HttpRouteConfigModel` — top-level config (name, custom_domains, rules)
  - `HttpRouteRuleConfig` — a rule with description, routes (match conditions), and targets
  - `HttpRouteMatchConfig` — match on `path` (exact), `prefix`, or `path_separated_prefix`; optional `case_sensitive`
  - `HttpRouteActionConfig` — optional `prefix_rewrite`
  - `HttpRouteTargetConfig` — `container_app` (name, required), optional `revision`, `label`, `weight`
- [ ] New `http_route_config()` builder function (or class) in `az_app` component that creates `app.HttpRouteConfig` resources
- [ ] `HttpRouteConfig` resource receives `environment_name` and `resource_group_name` from the environment output ref
- [ ] Add `http_routes: list[HttpRouteConfigModel] | None = None` field to `AppWorkloadConfig`
- [ ] Wire `http_routes` into the `deploy()` function in `app_workload_base.py`, creating route configs after apps are created (so app names are available)
- [ ] Targets can reference apps by name — either apps defined in the same workload config or external app names (string)
- [ ] Validation: each rule must have at least one target; target weights within a rule must sum to 100 when multiple targets with weights are specified
- [ ] Validation: match must specify exactly one of `path`, `prefix`, or `path_separated_prefix`
- [ ] Unit tests for all config models (validation, edge cases, happy paths)
- [ ] Unit tests for the builder function (Pulumi resource args generation)

### Should Have (P1)

- [ ] Custom domain bindings on routes (`CustomDomainConfig` reuse from existing ingress model or new route-specific model using `app.CustomDomainArgs`)
- [ ] Stack exports for created route configs (id, name) so downstream stacks can reference them

### Nice to Have (P2)

- [ ] Pulumi warning when targeting an app not defined in the same workload (user may have a typo vs. cross-stack reference)

## Non-Functional Requirements

- **Performance:** No impact — this is a declarative Pulumi resource, provisioned at deploy time
- **Security:** Custom domain certificate IDs must be valid Azure resource IDs (validated via `AzureIdRef`)
- **Backwards Compatibility:** Fully additive — new optional field on `AppWorkloadConfig`, no changes to existing configs

## Edge Cases & Error Handling

| Scenario | Expected Behavior |
|----------|-------------------|
| No `http_routes` configured | No `HttpRouteConfig` resources created (current behavior preserved) |
| Rule with single target, no weight | Valid — Azure defaults weight to 100 |
| Rule with multiple targets, weights don't sum to 100 | Pydantic validation error at config time |
| Match specifies both `path` and `prefix` | Pydantic validation error — must be exactly one |
| Match specifies none of path/prefix/path_separated_prefix | Pydantic validation error |
| Target references app name not in current workload | Allowed (could be cross-stack app name); optional P2 warning |
| Empty rules list | Pydantic validation error — at least one rule required |
| Duplicate route config names | Pydantic validation error |

## Affected Components/Bases

- `components/orbitcloud_graviton/az_app/` — new file `http_route.py` with config models and builder
- `components/orbitcloud_graviton/az_app/__init__.py` — export new public types
- `bases/orbitcloud_graviton/app_workload/app_workload_base.py` — add `http_routes` field and creation logic
- `test/` — new test file(s) for http route config models and builder

## Out of Scope

- Header-based routing (not supported by the Azure API yet)
- TCP route configs (separate Azure resource, not part of this feature)
- Automatic revision management / deployment strategies (this just configures routing rules)
- Changes to the `ContainerAppEnv` component (route config is created at workload level, not env level)

## Dependencies

- `pulumi-azure-native` SDK — confirmed `app.HttpRouteConfig`, `app.HttpRouteConfigArgs`, `app.HttpRouteRuleArgs`, `app.HttpRouteMatchArgs`, `app.HttpRouteActionArgs`, `app.HttpRouteTargetArgs` all exist in current provider version
- Requires a `ContainerAppEnv` to already exist (referenced via `environment_output_ref` on apps)
- Container apps must be created before route configs (route targets reference app names)

## Pulumi SDK Types Reference

```python
from pulumi_azure_native import app

app.HttpRouteConfig(resource_name, args=HttpRouteConfigArgs(...))

app.HttpRouteConfigArgs(
    environment_name: str,           # Required
    resource_group_name: str,        # Required
    http_route_name: str | None,     # Optional (auto-named if omitted)
    properties: HttpRouteConfigPropertiesArgs | None,
)

app.HttpRouteConfigPropertiesArgs(
    custom_domains: list[CustomDomainArgs] | None,
    rules: list[HttpRouteRuleArgs] | None,
)

app.HttpRouteRuleArgs(
    description: str | None,
    routes: list[HttpRouteArgs] | None,
    targets: list[HttpRouteTargetArgs] | None,
)

app.HttpRouteArgs(
    action: HttpRouteActionArgs | None,
    match: HttpRouteMatchArgs | None,
)

app.HttpRouteMatchArgs(
    case_sensitive: bool | None,          # Default: True
    path: str | None,                     # Exact match
    path_separated_prefix: str | None,    # Prefix match (path-separated)
    prefix: str | None,                   # Prefix match
)

app.HttpRouteActionArgs(
    prefix_rewrite: str | None,
)

app.HttpRouteTargetArgs(
    container_app: str,           # Required — app name
    label: str | None,
    revision: str | None,
    weight: int | None,
)
```

## Acceptance Criteria

- [ ] Can define `http_routes` in Pulumi stack config YAML and have `HttpRouteConfig` resources created
- [ ] Route rules correctly match on path, prefix, or path_separated_prefix
- [ ] Weighted targets route traffic to specified container apps/revisions
- [ ] Custom domains can be bound to route configs
- [ ] Prefix rewrite actions work correctly
- [ ] Invalid configs (bad match combos, weight sums, missing targets) fail with clear Pydantic errors
- [ ] All new code has unit test coverage
- [ ] No changes to existing container app or environment behavior when `http_routes` is not configured

## Example YAML Configuration

```yaml
config:
  workload:http_routes:
    - name: api-gateway-routes
      rules:
        - description: "Route /api/v1 to backend-api app"
          routes:
            - match:
                path_separated_prefix: "/api/v1"
              action:
                prefix_rewrite: "/"
          targets:
            - container_app: "backend-api"
              weight: 80
            - container_app: "backend-api-canary"
              weight: 20
        - description: "Route /web to frontend app"
          routes:
            - match:
                prefix: "/web"
          targets:
            - container_app: "frontend"
      custom_domains:
        - name: "api.example.com"
          certificate_id: "/subscriptions/.../certificates/cert-1"
          ssl: SniEnabled
```

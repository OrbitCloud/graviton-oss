# Task 01: Pydantic Config Models for HTTP Route

> Status: done

## Goal
Create all Pydantic config models in `components/orbitcloud_graviton/az_app/http_route.py`.

## Acceptance Criteria
- [ ] HttpRouteMatchConfig with exactly-one-of validation (path/prefix/path_separated_prefix)
- [ ] HttpRouteActionConfig with optional prefix_rewrite
- [ ] HttpRouteTargetConfig with container_app (required), optional revision/label/weight
- [ ] HttpRouteRuleConfig with description, routes, targets; at least one target required
- [ ] HttpRouteConfigModel with name, optional custom_domains, rules (at least one required)
- [ ] Weight validation: multi-target rules with weights must sum to 100
- [ ] All models use ConfigDict(extra="forbid")

## Notes
Follow patterns from resiliency.py and ingress.py.

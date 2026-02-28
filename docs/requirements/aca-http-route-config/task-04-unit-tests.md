# Task 04: Unit Tests

> Status: done

## Goal
Comprehensive unit tests for all config models and builder function.

## Acceptance Criteria
- [ ] Tests for HttpRouteMatchConfig (happy path, exactly-one-of validation, none set, multiple set)
- [ ] Tests for HttpRouteTargetConfig (happy path, required fields)
- [ ] Tests for HttpRouteRuleConfig (happy path, empty targets, weight validation)
- [ ] Tests for HttpRouteConfigModel (happy path, empty rules, duplicate names not validated at model level)
- [ ] Tests for builder function (Pulumi resource args generation)
- [ ] All tests pass with make test

## Notes
Follow test pattern from test_resiliency_config.py (importlib workaround for Pulumi runtime).

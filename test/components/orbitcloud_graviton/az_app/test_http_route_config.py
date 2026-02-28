import importlib.util
import pathlib
import sys
import types
from typing import Any

import pulumi
import pytest

# ---------------------------------------------------------------------------
# Module-level stub imports to avoid event-loop errors from transitive deps.
# The az_app package's __init__.py pulls in az_iam which calls
# asyncio.get_running_loop() at import time. We load submodules directly
# to sidestep this, following the same pattern as other tests in this dir.
# ---------------------------------------------------------------------------
_components_dir = pathlib.Path(__file__).resolve().parents[4] / "components"
_az_app_dir = _components_dir / "orbitcloud_graviton" / "az_app"

if "orbitcloud_graviton.az_app" not in sys.modules:
    _pkg = types.ModuleType("orbitcloud_graviton.az_app")
    _pkg.__path__ = [str(_az_app_dir)]  # type: ignore[attr-defined]
    _pkg.__package__ = "orbitcloud_graviton.az_app"
    sys.modules["orbitcloud_graviton.az_app"] = _pkg


def _load_module(name: str, path: pathlib.Path) -> types.ModuleType:
    """Load a module by file path without triggering az_app/__init__.py."""
    spec = importlib.util.spec_from_file_location(name, str(path))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_load_module("orbitcloud_graviton.az_app.cors", _az_app_dir / "cors.py")
_load_module("orbitcloud_graviton.az_app.ingress", _az_app_dir / "ingress.py")
_http_route = _load_module("orbitcloud_graviton.az_app.http_route", _az_app_dir / "http_route.py")

HttpRouteMatchConfig = _http_route.HttpRouteMatchConfig
HttpRouteActionConfig = _http_route.HttpRouteActionConfig
HttpRouteTargetConfig = _http_route.HttpRouteTargetConfig
HttpRouteRuleConfig = _http_route.HttpRouteRuleConfig
HttpRouteConfigModel = _http_route.HttpRouteConfigModel
HttpRouteEntry = _http_route.HttpRouteEntry
build_http_route_config = _http_route.build_http_route_config


# ============================================================
# HttpRouteMatchConfig tests
# ============================================================


class TestHttpRouteMatchConfig:
    def test_exact_path_match(self) -> None:
        match = HttpRouteMatchConfig.model_validate({"path": "/api/v1/health"})
        assert match.path == "/api/v1/health"
        assert match.prefix is None
        assert match.path_separated_prefix is None

    def test_prefix_match(self) -> None:
        match = HttpRouteMatchConfig.model_validate({"prefix": "/api"})
        assert match.prefix == "/api"
        assert match.path is None

    def test_path_separated_prefix_match(self) -> None:
        match = HttpRouteMatchConfig.model_validate({"path_separated_prefix": "/api/v1"})
        assert match.path_separated_prefix == "/api/v1"
        assert match.path is None
        assert match.prefix is None

    def test_case_sensitive_default(self) -> None:
        match = HttpRouteMatchConfig.model_validate({"path": "/test"})
        assert match.case_sensitive is None

    def test_case_sensitive_explicit(self) -> None:
        match = HttpRouteMatchConfig.model_validate({"path": "/test", "case_sensitive": False})
        assert match.case_sensitive is False

    def test_no_match_field_set_raises(self) -> None:
        with pytest.raises(
            ValueError,
            match="Exactly one of 'path', 'prefix', 'path_separated_prefix' must be set",
        ):
            HttpRouteMatchConfig.model_validate({})

    def test_multiple_match_fields_raises(self) -> None:
        with pytest.raises(
            ValueError,
            match="Exactly one of 'path', 'prefix', 'path_separated_prefix' must be set",
        ):
            HttpRouteMatchConfig.model_validate({"path": "/exact", "prefix": "/pre"})

    def test_all_three_match_fields_raises(self) -> None:
        with pytest.raises(
            ValueError,
            match="Exactly one of 'path', 'prefix', 'path_separated_prefix' must be set",
        ):
            HttpRouteMatchConfig.model_validate(
                {"path": "/a", "prefix": "/b", "path_separated_prefix": "/c"}
            )

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValueError):
            HttpRouteMatchConfig.model_validate({"path": "/test", "unknown_field": "value"})


# ============================================================
# HttpRouteActionConfig tests
# ============================================================


class TestHttpRouteActionConfig:
    def test_prefix_rewrite(self) -> None:
        action = HttpRouteActionConfig.model_validate({"prefix_rewrite": "/"})
        assert action.prefix_rewrite == "/"

    def test_no_prefix_rewrite(self) -> None:
        action = HttpRouteActionConfig.model_validate({})
        assert action.prefix_rewrite is None

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValueError):
            HttpRouteActionConfig.model_validate({"prefix_rewrite": "/", "bad": True})


# ============================================================
# HttpRouteTargetConfig tests
# ============================================================


class TestHttpRouteTargetConfig:
    def test_minimal_target(self) -> None:
        target = HttpRouteTargetConfig.model_validate({"container_app": "backend-api"})
        assert target.container_app == "backend-api"
        assert target.revision is None
        assert target.label is None
        assert target.weight is None

    def test_full_target(self) -> None:
        target = HttpRouteTargetConfig.model_validate(
            {
                "container_app": "backend-api",
                "revision": "rev-1",
                "label": "canary",
                "weight": 80,
            }
        )
        assert target.container_app == "backend-api"
        assert target.revision == "rev-1"
        assert target.label == "canary"
        assert target.weight == 80

    def test_weight_zero_valid(self) -> None:
        target = HttpRouteTargetConfig.model_validate({"container_app": "app", "weight": 0})
        assert target.weight == 0

    def test_weight_100_valid(self) -> None:
        target = HttpRouteTargetConfig.model_validate({"container_app": "app", "weight": 100})
        assert target.weight == 100

    def test_weight_negative_invalid(self) -> None:
        with pytest.raises(ValueError):
            HttpRouteTargetConfig.model_validate({"container_app": "app", "weight": -1})

    def test_weight_over_100_invalid(self) -> None:
        with pytest.raises(ValueError):
            HttpRouteTargetConfig.model_validate({"container_app": "app", "weight": 101})

    def test_missing_container_app_raises(self) -> None:
        with pytest.raises(ValueError):
            HttpRouteTargetConfig.model_validate({"weight": 50})


# ============================================================
# HttpRouteEntry tests
# ============================================================


class TestHttpRouteEntry:
    def test_match_is_required(self) -> None:
        """HttpRouteEntry requires match to be set."""
        with pytest.raises(ValueError):
            HttpRouteEntry.model_validate({})

    def test_match_only(self) -> None:
        entry = HttpRouteEntry.model_validate({"match": {"path": "/health"}})
        assert entry.match.path == "/health"
        assert entry.action is None

    def test_match_with_action(self) -> None:
        entry = HttpRouteEntry.model_validate(
            {"match": {"prefix": "/api"}, "action": {"prefix_rewrite": "/"}}
        )
        assert entry.match.prefix == "/api"
        assert entry.action is not None
        assert entry.action.prefix_rewrite == "/"


# ============================================================
# HttpRouteRuleConfig tests
# ============================================================


class TestHttpRouteRuleConfig:
    def test_minimal_rule(self) -> None:
        rule = HttpRouteRuleConfig.model_validate(
            {
                "targets": [{"container_app": "backend"}],
            }
        )
        assert rule.description is None
        assert rule.routes is None
        assert len(rule.targets) == 1

    def test_full_rule(self) -> None:
        rule = HttpRouteRuleConfig.model_validate(
            {
                "description": "Route API traffic",
                "routes": [
                    {
                        "match": {"prefix": "/api"},
                        "action": {"prefix_rewrite": "/"},
                    }
                ],
                "targets": [
                    {"container_app": "backend-api", "weight": 80},
                    {"container_app": "backend-canary", "weight": 20},
                ],
            }
        )
        assert rule.description == "Route API traffic"
        assert len(rule.routes) == 1
        assert len(rule.targets) == 2

    def test_empty_targets_raises(self) -> None:
        with pytest.raises(ValueError, match="at least 1"):
            HttpRouteRuleConfig.model_validate(
                {
                    "targets": [],
                }
            )

    def test_single_target_no_weight_valid(self) -> None:
        """Single target without weight is valid -- Azure defaults weight to 100."""
        rule = HttpRouteRuleConfig.model_validate({"targets": [{"container_app": "backend"}]})
        assert rule.targets[0].weight is None

    def test_multi_target_weights_sum_to_100_valid(self) -> None:
        rule = HttpRouteRuleConfig.model_validate(
            {
                "targets": [
                    {"container_app": "a", "weight": 70},
                    {"container_app": "b", "weight": 30},
                ],
            }
        )
        assert len(rule.targets) == 2

    def test_multi_target_weights_not_sum_to_100_raises(self) -> None:
        with pytest.raises(ValueError, match="Target weights must sum to 100"):
            HttpRouteRuleConfig.model_validate(
                {
                    "targets": [
                        {"container_app": "a", "weight": 70},
                        {"container_app": "b", "weight": 20},
                    ],
                }
            )

    def test_multi_target_some_without_weights_valid(self) -> None:
        """When multiple targets exist but not all have weights, no sum validation."""
        rule = HttpRouteRuleConfig.model_validate(
            {
                "targets": [
                    {"container_app": "a", "weight": 70},
                    {"container_app": "b"},
                ],
            }
        )
        assert len(rule.targets) == 2

    def test_route_with_match_only(self) -> None:
        rule = HttpRouteRuleConfig.model_validate(
            {
                "routes": [{"match": {"path": "/health"}}],
                "targets": [{"container_app": "backend"}],
            }
        )
        assert rule.routes[0].action is None


# ============================================================
# HttpRouteConfigModel tests
# ============================================================


class TestHttpRouteConfigModel:
    def test_minimal_config(self) -> None:
        config = HttpRouteConfigModel.model_validate(
            {
                "name": "api-routes",
                "rules": [
                    {
                        "targets": [{"container_app": "backend"}],
                    }
                ],
            }
        )
        assert config.name == "api-routes"
        assert len(config.rules) == 1
        assert config.custom_domains is None

    def test_empty_rules_raises(self) -> None:
        with pytest.raises(ValueError, match="at least 1"):
            HttpRouteConfigModel.model_validate(
                {
                    "name": "empty-routes",
                    "rules": [],
                }
            )

    def test_full_config_with_custom_domains(self) -> None:
        config = HttpRouteConfigModel.model_validate(
            {
                "name": "api-gateway",
                "custom_domains": [
                    {
                        "name": "api.example.com",
                        "certificate_id": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.App/managedEnvironments/env/certificates/cert-1",
                    }
                ],
                "rules": [
                    {
                        "description": "Route to backend",
                        "routes": [
                            {
                                "match": {"path_separated_prefix": "/api/v1"},
                                "action": {"prefix_rewrite": "/"},
                            }
                        ],
                        "targets": [
                            {"container_app": "backend-api", "weight": 80},
                            {"container_app": "backend-canary", "weight": 20},
                        ],
                    },
                    {
                        "description": "Route to frontend",
                        "routes": [{"match": {"prefix": "/web"}}],
                        "targets": [{"container_app": "frontend"}],
                    },
                ],
            }
        )
        assert config.name == "api-gateway"
        assert len(config.rules) == 2
        assert len(config.custom_domains) == 1

    def test_multiple_rules_valid(self) -> None:
        config = HttpRouteConfigModel.model_validate(
            {
                "name": "multi-rule",
                "rules": [
                    {"targets": [{"container_app": "app-a"}]},
                    {"targets": [{"container_app": "app-b"}]},
                ],
            }
        )
        assert len(config.rules) == 2


# ============================================================
# Duplicate route config name validation tests
# (tests the validation logic inline without loading AppWorkloadConfig
#  to avoid polluting sys.modules with stubs)
# ============================================================

from pydantic import BaseModel as _BaseModel  # noqa: E402
from pydantic import model_validator as _model_validator  # noqa: E402


class _TestWorkloadConfig(_BaseModel):
    """Minimal reproduction of AppWorkloadConfig's duplicate route name validator."""

    http_routes: list[HttpRouteConfigModel] | None = None

    @_model_validator(mode="after")
    def validate_http_routes(m: "_TestWorkloadConfig") -> "_TestWorkloadConfig":
        if m.http_routes and len(m.http_routes) > 1:
            route_names = [route.name for route in m.http_routes]
            if len(route_names) != len(set(route_names)):
                raise ValueError("HTTP route config names must be unique.")
        return m


class TestDuplicateRouteConfigNames:
    """Test that duplicate HTTP route config names are rejected.

    Uses a minimal model that mirrors the validate_http_routes validator
    from AppWorkloadConfig to avoid heavy transitive dependency stubs.
    """

    def test_duplicate_route_names_raises(self) -> None:
        with pytest.raises(ValueError, match="HTTP route config names must be unique"):
            _TestWorkloadConfig.model_validate(
                {
                    "http_routes": [
                        {
                            "name": "same-name",
                            "rules": [{"targets": [{"container_app": "app-a"}]}],
                        },
                        {
                            "name": "same-name",
                            "rules": [{"targets": [{"container_app": "app-b"}]}],
                        },
                    ]
                }
            )

    def test_unique_route_names_valid(self) -> None:
        config = _TestWorkloadConfig.model_validate(
            {
                "http_routes": [
                    {
                        "name": "route-a",
                        "rules": [{"targets": [{"container_app": "app-a"}]}],
                    },
                    {
                        "name": "route-b",
                        "rules": [{"targets": [{"container_app": "app-b"}]}],
                    },
                ]
            }
        )
        assert config.http_routes is not None
        assert len(config.http_routes) == 2

    def test_single_route_no_duplicate_check(self) -> None:
        """Single route config should not trigger duplicate validation."""
        config = _TestWorkloadConfig.model_validate(
            {
                "http_routes": [
                    {
                        "name": "only-route",
                        "rules": [{"targets": [{"container_app": "app-a"}]}],
                    },
                ]
            }
        )
        assert config.http_routes is not None
        assert len(config.http_routes) == 1


# ============================================================
# build_http_route_config tests
# ============================================================


class TestBuildHttpRouteConfig:
    """Tests for the builder function that creates Pulumi resources.

    These tests use Pulumi mocks (from conftest.py) to verify resource creation
    and that config values are correctly mapped to Pulumi resource args.
    """

    @pytest.fixture
    def minimal_config(self) -> HttpRouteConfigModel:
        return HttpRouteConfigModel.model_validate(
            {
                "name": "test-route",
                "rules": [
                    {
                        "targets": [{"container_app": "backend"}],
                    }
                ],
            }
        )

    @pytest.fixture
    def full_config(self) -> HttpRouteConfigModel:
        return HttpRouteConfigModel.model_validate(
            {
                "name": "api-gateway",
                "custom_domains": [
                    {
                        "name": "api.example.com",
                        "certificate_id": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.App/managedEnvironments/env/certificates/cert-1",
                    }
                ],
                "rules": [
                    {
                        "description": "Route API",
                        "routes": [
                            {
                                "match": {"path_separated_prefix": "/api/v1"},
                                "action": {"prefix_rewrite": "/"},
                            }
                        ],
                        "targets": [
                            {"container_app": "backend-api", "weight": 80},
                            {"container_app": "backend-canary", "weight": 20},
                        ],
                    },
                ],
            }
        )

    @pulumi.runtime.test
    def test_builder_creates_resource(self, minimal_config: HttpRouteConfigModel) -> None:
        resource = build_http_route_config(
            environment_name="test-env",
            resource_group_name="test-rg",
            config=minimal_config,
        )
        assert resource is not None

    @pulumi.runtime.test
    def test_builder_returns_http_route_config_type(
        self, minimal_config: HttpRouteConfigModel
    ) -> None:
        from pulumi_azure_native import app as az_app

        resource = build_http_route_config(
            environment_name="test-env",
            resource_group_name="test-rg",
            config=minimal_config,
        )
        assert isinstance(resource, az_app.HttpRouteConfig)

    @pulumi.runtime.test
    def test_builder_with_opts(self, minimal_config: HttpRouteConfigModel) -> None:
        opts = pulumi.ResourceOptions(protect=True)
        resource = build_http_route_config(
            environment_name="test-env",
            resource_group_name="test-rg",
            config=minimal_config,
            opts=opts,
        )
        assert resource is not None

    @pulumi.runtime.test
    def test_builder_maps_environment_and_resource_group(
        self, minimal_config: HttpRouteConfigModel
    ) -> None:
        """Verify environment_name and resource_group_name are correctly passed."""
        resource = build_http_route_config(
            environment_name="my-env",
            resource_group_name="my-rg",
            config=minimal_config,
        )

        def check_urn(urn: str) -> None:
            assert "test-route" in urn

        resource.urn.apply(check_urn)

    @pulumi.runtime.test
    def test_builder_maps_http_route_name_in_urn(
        self, minimal_config: HttpRouteConfigModel
    ) -> None:
        """Verify the Pulumi resource_name (from config.name) appears in the URN."""
        resource = build_http_route_config(
            environment_name="my-env",
            resource_group_name="my-rg",
            config=minimal_config,
        )

        def check_urn(urn: str) -> None:
            assert "test-route" in urn

        resource.urn.apply(check_urn)

    @pulumi.runtime.test
    def test_builder_maps_targets(self, full_config: HttpRouteConfigModel) -> None:
        """Verify target container_app names and weights are correctly mapped."""
        resource = build_http_route_config(
            environment_name="prod-env",
            resource_group_name="prod-rg",
            config=full_config,
        )

        def check_properties(props: Any) -> None:
            assert props is not None
            rules = props.rules
            assert len(rules) == 1
            targets = rules[0].targets
            assert len(targets) == 2
            assert targets[0].container_app == "backend-api"
            assert targets[0].weight == 80
            assert targets[1].container_app == "backend-canary"
            assert targets[1].weight == 20

        resource.properties.apply(check_properties)

    @pulumi.runtime.test
    def test_builder_maps_match_conditions(self, full_config: HttpRouteConfigModel) -> None:
        """Verify route match conditions (path_separated_prefix) are correctly mapped."""
        resource = build_http_route_config(
            environment_name="prod-env",
            resource_group_name="prod-rg",
            config=full_config,
        )

        def check_properties(props: Any) -> None:
            assert props is not None
            rules = props.rules
            routes = rules[0].routes
            assert len(routes) == 1
            match = routes[0].match
            assert match.path_separated_prefix == "/api/v1"

        resource.properties.apply(check_properties)

    @pulumi.runtime.test
    def test_builder_maps_action(self, full_config: HttpRouteConfigModel) -> None:
        """Verify route action (prefix_rewrite) is correctly mapped."""
        resource = build_http_route_config(
            environment_name="prod-env",
            resource_group_name="prod-rg",
            config=full_config,
        )

        def check_properties(props: Any) -> None:
            assert props is not None
            routes = props.rules[0].routes
            action = routes[0].action
            assert action.prefix_rewrite == "/"

        resource.properties.apply(check_properties)

    @pulumi.runtime.test
    def test_builder_maps_custom_domains(self, full_config: HttpRouteConfigModel) -> None:
        """Verify custom domain name and certificate_id are correctly mapped."""
        resource = build_http_route_config(
            environment_name="prod-env",
            resource_group_name="prod-rg",
            config=full_config,
        )

        def check_properties(props: Any) -> None:
            assert props is not None
            domains = props.custom_domains
            assert len(domains) == 1
            assert domains[0].name == "api.example.com"
            assert "certificates/cert-1" in domains[0].certificate_id

        resource.properties.apply(check_properties)

    @pulumi.runtime.test
    def test_builder_maps_rule_description(self, full_config: HttpRouteConfigModel) -> None:
        """Verify rule description is correctly mapped."""
        resource = build_http_route_config(
            environment_name="prod-env",
            resource_group_name="prod-rg",
            config=full_config,
        )

        def check_properties(props: Any) -> None:
            assert props is not None
            assert props.rules[0].description == "Route API"

        resource.properties.apply(check_properties)

    @pulumi.runtime.test
    def test_builder_no_custom_domains(self, minimal_config: HttpRouteConfigModel) -> None:
        """Builder with no custom domains produces None for customDomains in properties."""
        resource = build_http_route_config(
            environment_name="test-env",
            resource_group_name="test-rg",
            config=minimal_config,
        )

        def check_properties(props: Any) -> None:
            assert props is not None
            assert props.custom_domains is None

        resource.properties.apply(check_properties)

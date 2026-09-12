"""Tests for the Azure Front Door component."""

from uuid import UUID

import pulumi
import pytest
from pulumi_azure_native import cdn

from orbitcloud_graviton.pulumi_mocks import set_mocks

set_mocks()

from orbitcloud_graviton.az_frontdoor import (  # noqa: E402
    FrontDoor,
    FrontDoorConfig,
    FrontDoorCustomDomainConfig,
    FrontDoorEndpointConfig,
    FrontDoorOriginConfig,
    FrontDoorOriginGroupConfig,
    FrontDoorRouteConfig,
    FrontDoorSku,
)
from orbitcloud_graviton.pulumi_lib import AzureStack  # noqa: E402

WAF_POLICY_ID = (
    "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg"
    "/providers/Microsoft.Network/frontDoorWebApplicationFirewallPolicies/waf"
)
WORKSPACE_ID = (
    "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg"
    "/providers/Microsoft.OperationalInsights/workspaces/law"
)


def _make_stack(**overrides) -> AzureStack:
    defaults = {
        "subscription_id": UUID("00000000-0000-0000-0000-000000000000"),
        "tenant_id": UUID("00000000-0000-0000-0000-000000000000"),
        "location": "northeurope",
        "workload_name": "testworkload",
        "env": "test",
        "skip_exports": True,
    }
    defaults.update(overrides)
    return AzureStack(**defaults)


def _origin_group(name: str = "web") -> FrontDoorOriginGroupConfig:
    return FrontDoorOriginGroupConfig(
        name=name,
        origins=[FrontDoorOriginConfig(name=f"{name}-origin", host_name="app.example.com")],
    )


def _config(**overrides) -> FrontDoorConfig:
    defaults = {
        "origin_groups": [_origin_group()],
        "endpoints": [
            FrontDoorEndpointConfig(
                name="public",
                routes=[FrontDoorRouteConfig(name="default", origin_group="web")],
            )
        ],
    }
    defaults.update(overrides)
    return FrontDoorConfig(**defaults)


# --- Config ---


def test_config_defaults() -> None:
    config = FrontDoorConfig()

    assert config.sku is FrontDoorSku.STANDARD
    assert config.origin_response_timeout_seconds == 60
    assert config.endpoints == []


def test_config_forbids_extra() -> None:
    with pytest.raises(ValueError):
        FrontDoorConfig.model_validate({"unknown": "value"})


def test_origin_priority_is_bounded() -> None:
    with pytest.raises(ValueError):
        FrontDoorOriginConfig(name="o", host_name="app.example.com", priority=6)


def test_route_defaults() -> None:
    route = FrontDoorRouteConfig(name="default", origin_group="web")

    assert route.patterns_to_match == ["/*"]
    assert route.https_redirect is True
    assert route.forwarding_protocol is cdn.ForwardingProtocol.HTTPS_ONLY


# --- Validation ---


def test_route_with_unknown_origin_group_is_rejected() -> None:
    config = FrontDoorConfig(
        origin_groups=[_origin_group()],
        endpoints=[
            FrontDoorEndpointConfig(
                name="public",
                routes=[FrontDoorRouteConfig(name="default", origin_group="missing")],
            )
        ],
    )

    with pytest.raises(ValueError, match="unknown origin group"):
        FrontDoor(stack=_make_stack(), config=config)


def test_route_with_unknown_custom_domain_is_rejected() -> None:
    config = FrontDoorConfig(
        origin_groups=[_origin_group()],
        endpoints=[
            FrontDoorEndpointConfig(
                name="public",
                routes=[
                    FrontDoorRouteConfig(
                        name="default", origin_group="web", custom_domains=["missing"]
                    )
                ],
            )
        ],
    )

    with pytest.raises(ValueError, match="unknown custom domain"):
        FrontDoor(stack=_make_stack(), config=config)


def test_waf_requires_premium_sku() -> None:
    with pytest.raises(ValueError, match="Premium_AzureFrontDoor"):
        FrontDoor(stack=_make_stack(), config=_config(waf_policy_id=WAF_POLICY_ID))


# --- Resources ---


@pulumi.runtime.test
def test_profile_created() -> None:
    component = FrontDoor(stack=_make_stack(), config=_config())

    assert isinstance(component.profile, cdn.Profile)
    assert component.profile._name == "afd-testworkload-test-neu-01"


@pulumi.runtime.test
def test_profile_is_global() -> None:
    component = FrontDoor(stack=_make_stack(), config=_config())

    def check(location: str) -> None:
        assert location == "global"

    return component.profile.location.apply(check)  # type: ignore[return-value]


@pulumi.runtime.test
def test_children_created_for_each_config_entry() -> None:
    component = FrontDoor(stack=_make_stack(), config=_config())

    assert set(component.origin_groups) == {"web"}
    assert set(component.origins) == {"web-origin"}
    assert set(component.endpoints) == {"public"}
    assert set(component.routes) == {"default"}


@pulumi.runtime.test
def test_origin_host_header_defaults_to_host_name() -> None:
    component = FrontDoor(stack=_make_stack(), config=_config())

    def check(host_header: str) -> None:
        assert host_header == "app.example.com"

    return component.origins["web-origin"].origin_host_header.apply(check)  # type: ignore[return-value]


@pulumi.runtime.test
def test_custom_domain_created() -> None:
    config = _config(
        custom_domains=[
            FrontDoorCustomDomainConfig(name="www", host_name="www.example.com"),
        ],
    )
    component = FrontDoor(stack=_make_stack(), config=config)

    assert set(component.custom_domains) == {"www"}


@pulumi.runtime.test
def test_premium_sku_with_waf_creates_security_policy() -> None:
    config = _config(sku=FrontDoorSku.PREMIUM, waf_policy_id=WAF_POLICY_ID)
    component = FrontDoor(stack=_make_stack(), config=config)

    assert isinstance(component.security_policy, cdn.SecurityPolicy)


@pulumi.runtime.test
def test_no_security_policy_without_waf() -> None:
    component = FrontDoor(stack=_make_stack(), config=_config())

    assert component.security_policy is None


@pulumi.runtime.test
def test_diagnostics_created_with_workspace() -> None:
    component = FrontDoor(stack=_make_stack(), config=_config(log_workspace_id=WORKSPACE_ID))

    assert component.diagnostic_settings is not None

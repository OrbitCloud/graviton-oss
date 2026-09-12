"""Tests for the App Service web app component."""

from uuid import UUID

import pulumi
import pytest
from pulumi_azure_native import web

from orbitcloud_graviton.pulumi_mocks import set_mocks

set_mocks()

from orbitcloud_graviton.az_appservice import (  # noqa: E402
    WebApp,
    WebAppConfig,
    WebAppIpRestrictionConfig,
)
from orbitcloud_graviton.pulumi_lib import AzureStack  # noqa: E402

PLAN_ID = (
    "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg"
    "/providers/Microsoft.Web/serverfarms/asp-testworkload-test-neu-01"
)
SUBNET_ID = (
    "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg"
    "/providers/Microsoft.Network/virtualNetworks/vnet/subnets/apps"
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


# --- Config ---


def test_config_defaults() -> None:
    config = WebAppConfig(plan_id=PLAN_ID)

    assert config.https_only is True
    assert config.always_on is True
    assert config.ftps_state is web.FtpsState.DISABLED
    assert config.min_tls_version is web.SupportedTlsVersions.SUPPORTED_TLS_VERSIONS_1_2
    assert config.system_assigned_identity is True


def test_config_requires_plan_id() -> None:
    with pytest.raises(ValueError):
        WebAppConfig.model_validate({})


def test_config_forbids_extra() -> None:
    with pytest.raises(ValueError):
        WebAppConfig.model_validate({"plan_id": PLAN_ID, "unknown": "value"})


def test_ip_restriction_priority_is_bounded() -> None:
    with pytest.raises(ValueError):
        WebAppIpRestrictionConfig(name="deny", priority=0)


# --- Resources ---


@pulumi.runtime.test
def test_web_app_created() -> None:
    component = WebApp(stack=_make_stack(), config=WebAppConfig(plan_id=PLAN_ID))

    assert isinstance(component.web_app, web.WebApp)
    assert component.web_app._name == "app-testworkload-test-neu-01"


@pulumi.runtime.test
def test_linux_kind_reserves_the_plan() -> None:
    component = WebApp(stack=_make_stack(), config=WebAppConfig(plan_id=PLAN_ID))

    def check(reserved: bool) -> None:
        assert reserved is True

    return component.web_app.reserved.apply(check)  # type: ignore[return-value]


@pulumi.runtime.test
def test_windows_kind_does_not_reserve_the_plan() -> None:
    component = WebApp(stack=_make_stack(), config=WebAppConfig(plan_id=PLAN_ID, kind="app"))

    def check(reserved: bool) -> None:
        assert reserved is False

    return component.web_app.reserved.apply(check)  # type: ignore[return-value]


@pulumi.runtime.test
def test_https_only_by_default() -> None:
    component = WebApp(stack=_make_stack(), config=WebAppConfig(plan_id=PLAN_ID))

    def check(https_only: bool) -> None:
        assert https_only is True

    return component.web_app.https_only.apply(check)  # type: ignore[return-value]


@pulumi.runtime.test
def test_app_settings_rendered_as_name_value_pairs() -> None:
    config = WebAppConfig(plan_id=PLAN_ID, app_settings={"WEBSITE_RUN_FROM_PACKAGE": "1"})
    component = WebApp(stack=_make_stack(), config=config)

    # App settings are input-only -- Azure never returns them on SiteConfigResponse,
    # so assert on what the component renders into the request.
    settings = component._app_settings()

    assert settings is not None
    assert [(s.name, s.value) for s in settings] == [("WEBSITE_RUN_FROM_PACKAGE", "1")]


@pulumi.runtime.test
def test_vnet_integration_sets_route_all() -> None:
    config = WebAppConfig(plan_id=PLAN_ID, vnet_subnet_id=SUBNET_ID)
    component = WebApp(stack=_make_stack(), config=config)

    def check(site_config) -> None:
        assert site_config.vnet_route_all_enabled is True

    return component.web_app.site_config.apply(check)  # type: ignore[return-value]


@pulumi.runtime.test
def test_no_vnet_route_all_without_subnet() -> None:
    component = WebApp(stack=_make_stack(), config=WebAppConfig(plan_id=PLAN_ID))

    def check(site_config) -> None:
        assert site_config.vnet_route_all_enabled is None

    return component.web_app.site_config.apply(check)  # type: ignore[return-value]


@pulumi.runtime.test
def test_ip_restrictions_rendered() -> None:
    config = WebAppConfig(
        plan_id=PLAN_ID,
        ip_restrictions_default_action="Deny",
        ip_restrictions=[
            WebAppIpRestrictionConfig(name="office", priority=100, ip_address="10.0.0.0/8"),
        ],
    )
    component = WebApp(stack=_make_stack(), config=config)

    def check(site_config) -> None:
        rules = site_config.ip_security_restrictions
        assert [r.name for r in rules] == ["office"]
        assert rules[0].ip_address == "10.0.0.0/8"
        assert site_config.ip_security_restrictions_default_action == "Deny"

    return component.web_app.site_config.apply(check)  # type: ignore[return-value]


@pulumi.runtime.test
def test_system_assigned_identity_by_default() -> None:
    component = WebApp(stack=_make_stack(), config=WebAppConfig(plan_id=PLAN_ID))

    def check(identity) -> None:
        assert identity.type == web.ManagedServiceIdentityType.SYSTEM_ASSIGNED

    return component.web_app.identity.apply(check)  # type: ignore[return-value]


@pulumi.runtime.test
def test_identity_can_be_disabled() -> None:
    config = WebAppConfig(plan_id=PLAN_ID, system_assigned_identity=False)
    component = WebApp(stack=_make_stack(), config=config)

    def check(identity) -> None:
        assert identity is None

    return component.web_app.identity.apply(check)  # type: ignore[return-value]


@pulumi.runtime.test
def test_public_network_access_can_be_disabled() -> None:
    config = WebAppConfig(plan_id=PLAN_ID, public_network_access=False)
    component = WebApp(stack=_make_stack(), config=config)

    def check(access: str) -> None:
        assert access == "Disabled"

    return component.web_app.public_network_access.apply(check)  # type: ignore[return-value]


@pulumi.runtime.test
def test_diagnostics_created_with_workspace() -> None:
    config = WebAppConfig(plan_id=PLAN_ID, log_workspace_id=WORKSPACE_ID)
    component = WebApp(stack=_make_stack(), config=config)

    assert component.diagnostic_settings is not None


@pulumi.runtime.test
def test_no_diagnostics_without_workspace() -> None:
    component = WebApp(stack=_make_stack(), config=WebAppConfig(plan_id=PLAN_ID))

    assert component.diagnostic_settings is None

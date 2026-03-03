"""Pulumi resource-creation tests for MysqlFlexibleServer.

These tests use Pulumi mocks to verify that the correct Azure resources
are created with the expected properties.
"""

import logging
from uuid import UUID

import pulumi
from pulumi_azure_native import dbformysql as mysql

from orbitcloud_graviton.az_network.types import PublicIpv4FirewallRule
from orbitcloud_graviton.pulumi_mocks import set_mocks

set_mocks()

from orbitcloud_graviton.az_mysql import (  # noqa: E402
    MysqlAuthConfig,
    MysqlDatabaseConfig,
    MysqlFlexibleServer,
    MysqlFlexibleServerConfig,
)
from orbitcloud_graviton.pulumi_lib import AzureStack, EntraStack  # noqa: E402

# --- Fixtures ---


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


def _make_entra() -> EntraStack:
    return EntraStack.model_validate({"azuread:tenantId": "00000000-0000-0000-0000-000000000000"})


# --- Tests ---


@pulumi.runtime.test
def test_server_created_with_defaults() -> None:
    stack = _make_stack()
    config = MysqlFlexibleServerConfig()
    component = MysqlFlexibleServer(stack=stack, entra_config=_make_entra(), config=config)

    assert isinstance(component.server, mysql.Server)


@pulumi.runtime.test
def test_auto_generated_password() -> None:
    stack = _make_stack()
    config = MysqlFlexibleServerConfig()
    component = MysqlFlexibleServer(stack=stack, entra_config=_make_entra(), config=config)

    # admin_password should be a Pulumi Output (from RandomPassword)
    assert isinstance(component.admin_password, pulumi.Output)


@pulumi.runtime.test
def test_explicit_password_used() -> None:
    stack = _make_stack()
    config = MysqlFlexibleServerConfig(
        authentication=MysqlAuthConfig(
            admin_password="my-explicit-pw"
        ),  # NOSONAR - test credential
    )
    component = MysqlFlexibleServer(stack=stack, entra_config=_make_entra(), config=config)

    assert component.admin_password == "my-explicit-pw"


@pulumi.runtime.test
def test_public_network_access_enabled_without_vnet() -> None:
    """Without VNet config, public network access should be ENABLED."""
    stack = _make_stack()
    config = MysqlFlexibleServerConfig()
    component = MysqlFlexibleServer(stack=stack, entra_config=_make_entra(), config=config)

    def check(args):
        public_access = args
        assert public_access == mysql.EnableStatusEnum.ENABLED

    component.server.network.public_network_access.apply(check)


@pulumi.runtime.test
def test_public_network_access_disabled_with_vnet() -> None:
    """With VNet config, public network access should be DISABLED."""
    from orbitcloud_graviton.az_mysql import MysqlNetworkConfig

    stack = _make_stack()
    config = MysqlFlexibleServerConfig(
        network=MysqlNetworkConfig(
            subnet_id="/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.Network/virtualNetworks/vnet/subnets/default",
            private_dns_zone_id="/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.Network/privateDnsZones/mysql.database.azure.com",
        ),
    )
    component = MysqlFlexibleServer(stack=stack, entra_config=_make_entra(), config=config)

    def check(args):
        public_access = args
        assert public_access == mysql.EnableStatusEnum.DISABLED

    component.server.network.public_network_access.apply(check)


@pulumi.runtime.test
def test_databases_created() -> None:
    stack = _make_stack()
    config = MysqlFlexibleServerConfig(
        databases=[
            MysqlDatabaseConfig(name="db1"),
            MysqlDatabaseConfig(name="db2", charset="latin1", collation="latin1_swedish_ci"),
        ],
    )
    component = MysqlFlexibleServer(stack=stack, entra_config=_make_entra(), config=config)

    assert len(component.databases) == 2
    assert all(isinstance(db, mysql.Database) for db in component.databases)


@pulumi.runtime.test
def test_no_databases_when_none() -> None:
    stack = _make_stack()
    config = MysqlFlexibleServerConfig()
    component = MysqlFlexibleServer(stack=stack, entra_config=_make_entra(), config=config)

    assert component.databases == []


@pulumi.runtime.test
def test_firewall_rules_created() -> None:
    stack = _make_stack()
    config = MysqlFlexibleServerConfig(
        allowed_public_networks=[
            PublicIpv4FirewallRule(name="office", cidr="8.8.8.0/24"),  # type: ignore[arg-type]  # NOSONAR
            PublicIpv4FirewallRule(name="vpn", cidr="1.2.3.0/24"),  # type: ignore[arg-type]  # NOSONAR
        ],
    )
    component = MysqlFlexibleServer(stack=stack, entra_config=_make_entra(), config=config)

    assert len(component.firewall_rules) == 2
    assert all(isinstance(r, mysql.FirewallRule) for r in component.firewall_rules)


@pulumi.runtime.test
def test_no_firewall_rules_when_none() -> None:
    stack = _make_stack()
    config = MysqlFlexibleServerConfig()
    component = MysqlFlexibleServer(stack=stack, entra_config=_make_entra(), config=config)

    assert component.firewall_rules == []


@pulumi.runtime.test
def test_azure_services_rule_created() -> None:
    stack = _make_stack()
    config = MysqlFlexibleServerConfig(allow_azure_services=True)
    component = MysqlFlexibleServer(stack=stack, entra_config=_make_entra(), config=config)

    assert isinstance(component.azure_services_rule, mysql.FirewallRule)


@pulumi.runtime.test
def test_no_azure_services_rule_by_default() -> None:
    stack = _make_stack()
    config = MysqlFlexibleServerConfig()
    component = MysqlFlexibleServer(stack=stack, entra_config=_make_entra(), config=config)

    assert component.azure_services_rule is None


@pulumi.runtime.test
def test_server_params_created() -> None:
    stack = _make_stack()
    config = MysqlFlexibleServerConfig(
        server_params={"max_connections": "200", "slow_query_log": "ON"},
    )
    component = MysqlFlexibleServer(stack=stack, entra_config=_make_entra(), config=config)

    assert component.server_params is not None
    assert len(component.server_params) == 2
    assert all(isinstance(p, mysql.Configuration) for p in component.server_params)


@pulumi.runtime.test
def test_no_server_params_when_none() -> None:
    stack = _make_stack()
    config = MysqlFlexibleServerConfig()
    component = MysqlFlexibleServer(stack=stack, entra_config=_make_entra(), config=config)

    assert component.server_params is None


@pulumi.runtime.test
def test_entra_admin_not_created_without_azure_environment() -> None:
    """When azure_environment is not set, no Entra admin should be created."""
    stack = _make_stack()
    config = MysqlFlexibleServerConfig()
    component = MysqlFlexibleServer(stack=stack, entra_config=_make_entra(), config=config)

    assert component.admins is None


@pulumi.runtime.test
def test_entra_admin_not_created_when_disabled() -> None:
    """When entra_auth=False, no Entra admin should be created."""
    stack = _make_stack()
    config = MysqlFlexibleServerConfig(
        authentication=MysqlAuthConfig(entra_auth=False),
    )
    component = MysqlFlexibleServer(stack=stack, entra_config=_make_entra(), config=config)

    assert component.admins is None


@pulumi.runtime.test
def test_entra_admin_created_with_azure_environment() -> None:
    """When azure_environment is set and entra_auth=True, Entra admin should be created."""
    from orbitcloud_graviton.pulumi_lib.azure_base import (
        AzureEnvironmentPulumiConfig,
        EntraEscApp,
    )

    stack = _make_stack(
        azure_environment=AzureEnvironmentPulumiConfig(
            pulumi_esc_app=EntraEscApp(
                name="test-esc-app",
                app_client_id=UUID("11111111-1111-1111-1111-111111111111"),
                app_object_id=UUID("22222222-2222-2222-2222-222222222222"),
                service_principal_id="sp-id",
                service_principal_object_id=UUID("33333333-3333-3333-3333-333333333333"),
            ),
            resource_group_name="rg-test",
        ),
    )
    config = MysqlFlexibleServerConfig()
    component = MysqlFlexibleServer(stack=stack, entra_config=_make_entra(), config=config)

    assert isinstance(component.admins, mysql.AzureADAdministrator)


@pulumi.runtime.test
def test_warning_logged_when_entra_auth_but_no_azure_environment(caplog) -> None:
    """A warning should be logged when entra_auth=True but azure_environment is missing."""
    stack = _make_stack()
    config = MysqlFlexibleServerConfig(authentication=MysqlAuthConfig(entra_auth=True))

    with caplog.at_level(logging.WARNING, logger="orbitcloud_graviton.az_mysql.flexibleserver"):
        MysqlFlexibleServer(stack=stack, entra_config=_make_entra(), config=config)

    assert any(
        "Entra authentication is enabled but azure_environment is not set" in r.message
        for r in caplog.records
    )


@pulumi.runtime.test
def test_no_warning_when_entra_auth_disabled(caplog) -> None:
    """No warning should be logged when entra_auth=False."""
    stack = _make_stack()
    config = MysqlFlexibleServerConfig(
        authentication=MysqlAuthConfig(entra_auth=False),
    )

    with caplog.at_level(logging.WARNING, logger="orbitcloud_graviton.az_mysql.flexibleserver"):
        MysqlFlexibleServer(stack=stack, entra_config=_make_entra(), config=config)

    assert not any("Entra authentication is enabled" in r.message for r in caplog.records)


@pulumi.runtime.test
def test_server_sku_properties() -> None:
    stack = _make_stack()
    config = MysqlFlexibleServerConfig()
    component = MysqlFlexibleServer(stack=stack, entra_config=_make_entra(), config=config)

    def check(args):
        sku_name, sku_tier = args
        assert sku_name == "Standard_B1ms"
        assert sku_tier == mysql.ServerSkuTier.BURSTABLE

    pulumi.Output.all(
        component.server.sku.name,
        component.server.sku.tier,
    ).apply(check)


@pulumi.runtime.test
def test_server_version() -> None:
    stack = _make_stack()
    config = MysqlFlexibleServerConfig(server_version="8.0.21")
    component = MysqlFlexibleServer(stack=stack, entra_config=_make_entra(), config=config)

    def check(version):
        assert version == "8.0.21"

    component.server.version.apply(check)

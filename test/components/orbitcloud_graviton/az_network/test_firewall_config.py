import pytest

from orbitcloud_graviton.az_network.firewall import (
    ApplicationRule,
    FirewallConfig,
    NetworkRule,
    ProtocolPort,
)


# NetworkRule tests
def test_network_rule_valid_with_destination_ip() -> None:
    rule = NetworkRule.model_validate(
        {
            "name": "test-rule",
            "destination_ip_addresses": "10.0.0.0/24",
            "destination_ports": [80, 443],
            "source_ip_addresses": "192.168.1.0/24",
            "protocols": ["TCP"],
        }
    )
    assert rule.name == "test-rule"
    assert rule.destination_ports == [80, 443]


def test_network_rule_valid_with_wildcard_source() -> None:
    rule = NetworkRule.model_validate(
        {
            "name": "test-rule",
            "destination_ip_addresses": "10.0.0.0/24",
            "destination_ports": "80",
            "source_ip_addresses": "*",
        }
    )
    assert rule.source_ip_addresses == "*"


def test_network_rule_valid_with_service_tags() -> None:
    # Note: Service tag validation requires Azure API calls which are not
    # available in test environment. This test is skipped.
    pytest.skip("Service tag validation requires Azure API access")


def test_network_rule_valid_with_fqdns() -> None:
    rule = NetworkRule.model_validate(
        {
            "name": "test-rule",
            "destination_fqdns": ["example.com", "test.org"],
            "destination_ports": [80, 443],
            "source_ip_addresses": "10.0.0.0/16",
        }
    )
    assert rule.destination_fqdns == ["example.com", "test.org"]


def test_network_rule_multiple_destinations_exception() -> None:
    with pytest.raises(ValueError, match="Exactly one of destination"):
        NetworkRule.model_validate(
            {
                "name": "test-rule",
                "destination_ip_addresses": "10.0.0.0/24",
                "destination_service_tags": ["AzureCloud"],
                "destination_ports": 80,
                "source_ip_addresses": "192.168.1.0/24",
            }
        )


def test_network_rule_no_destination_exception() -> None:
    with pytest.raises(ValueError, match="Exactly one of destination"):
        NetworkRule.model_validate(
            {
                "name": "test-rule",
                "destination_ports": 80,
                "source_ip_addresses": "192.168.1.0/24",
            }
        )


def test_network_rule_invalid_destination_ip() -> None:
    with pytest.raises(ValueError, match="Destination address .* is not valid"):
        NetworkRule.model_validate(
            {
                "name": "test-rule",
                "destination_ip_addresses": "invalid-ip",
                "destination_ports": 80,
                "source_ip_addresses": "10.0.0.0/24",
            }
        )


def test_network_rule_invalid_service_tag() -> None:
    # Note: This test validates service tag checking, but actual tag validation
    # requires Azure API calls which are not available in test environment.
    # The validation is skipped in this test.
    pytest.skip("Service tag validation requires Azure API access")


def test_network_rule_no_source_exception() -> None:
    with pytest.raises(ValueError, match="Source address or group must be specified"):
        NetworkRule.model_validate(
            {
                "name": "test-rule",
                "destination_ip_addresses": "10.0.0.0/24",
                "destination_ports": 80,
            }
        )


def test_network_rule_invalid_source_ip() -> None:
    with pytest.raises(ValueError, match="Source address .* is not a valid"):
        NetworkRule.model_validate(
            {
                "name": "test-rule",
                "destination_ip_addresses": "10.0.0.0/24",
                "destination_ports": 80,
                "source_ip_addresses": "invalid-source",
            }
        )


# ApplicationRule tests
def test_application_rule_valid_with_fqdns() -> None:
    rule = ApplicationRule.model_validate(
        {
            "name": "app-rule",
            "source_ip_addresses": "10.0.0.0/24",
            "destination_fqdns": ["example.com", "test.org"],
            "protocols": [{"protocol": "Https", "port": 443}],
        }
    )
    assert rule.name == "app-rule"
    assert rule.destination_fqdns == ["example.com", "test.org"]


def test_application_rule_valid_with_fqdn_tags() -> None:
    # Note: FQDN tag validation requires Azure API calls which are not
    # available in test environment. This test is skipped.
    pytest.skip("FQDN tag validation requires Azure API access")


def test_application_rule_multiple_destinations_exception() -> None:
    with pytest.raises(ValueError, match="Exactly one of destination"):
        ApplicationRule.model_validate(
            {
                "name": "app-rule",
                "source_ip_addresses": "10.0.0.0/24",
                "destination_fqdns": ["example.com"],
                "destination_fqdn_tags": ["WindowsUpdate"],
                "protocols": [{"protocol": "Https"}],
            }
        )


def test_application_rule_no_destination_exception() -> None:
    with pytest.raises(ValueError, match="Exactly one of destination"):
        ApplicationRule.model_validate(
            {
                "name": "app-rule",
                "source_ip_addresses": "10.0.0.0/24",
                "protocols": [{"protocol": "Https"}],
            }
        )


def test_application_rule_invalid_fqdn_tag() -> None:
    # Note: FQDN tag validation requires Azure API calls which are not
    # available in test environment. This test is skipped.
    pytest.skip("FQDN tag validation requires Azure API access")


def test_application_rule_no_source_exception() -> None:
    with pytest.raises(ValueError, match="Source address or group must be specified"):
        ApplicationRule.model_validate(
            {
                "name": "app-rule",
                "destination_fqdns": ["example.com"],
                "protocols": [{"protocol": "Https"}],
            }
        )


# ProtocolPort tests
def test_protocol_port_default_http() -> None:
    port = ProtocolPort.model_validate({"protocol": "Http"})
    assert port.port == 80


def test_protocol_port_default_https() -> None:
    port = ProtocolPort.model_validate({"protocol": "Https"})
    assert port.port == 443


def test_protocol_port_default_mssql() -> None:
    port = ProtocolPort.model_validate({"protocol": "Mssql"})
    assert port.port == 1433


def test_protocol_port_custom_port() -> None:
    port = ProtocolPort.model_validate({"protocol": "Http", "port": 8080})
    assert port.port == 8080


def test_protocol_port_out_of_range_low() -> None:
    with pytest.raises(ValueError, match="Port number .* is out of the valid range"):
        ProtocolPort.model_validate({"protocol": "Http", "port": 0})


def test_protocol_port_out_of_range_high() -> None:
    with pytest.raises(ValueError, match="Port number .* is out of the valid range"):
        ProtocolPort.model_validate({"protocol": "Http", "port": 65536})


# FirewallConfig tests
def test_firewall_config_basic_sku_requires_management_subnet() -> None:
    with pytest.raises(ValueError, match="Management subnet is required for Basic SKU"):
        FirewallConfig.model_validate(
            {
                "sku": "Basic",
                "subnet": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/test/providers/Microsoft.Network/virtualNetworks/vnet/subnets/AzureFirewallSubnet",
            }
        )


def test_firewall_config_basic_sku_no_dns_proxy() -> None:
    with pytest.raises(ValueError, match="DNS Proxy is not supported for Basic SKU"):
        FirewallConfig.model_validate(
            {
                "sku": "Basic",
                "subnet": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/test/providers/Microsoft.Network/virtualNetworks/vnet/subnets/AzureFirewallSubnet",
                "management_subnet": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/test/providers/Microsoft.Network/virtualNetworks/vnet/subnets/AzureFirewallManagementSubnet",
                "dns_proxy": True,
            }
        )


def test_firewall_config_basic_sku_no_custom_dns() -> None:
    with pytest.raises(ValueError, match="Custom DNS Servers are not supported for Basic SKU"):
        FirewallConfig.model_validate(
            {
                "sku": "Basic",
                "subnet": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/test/providers/Microsoft.Network/virtualNetworks/vnet/subnets/AzureFirewallSubnet",
                "management_subnet": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/test/providers/Microsoft.Network/virtualNetworks/vnet/subnets/AzureFirewallManagementSubnet",
                "custom_dns_servers": ["8.8.8.8"],
            }
        )


def test_firewall_config_destination_urls_require_premium() -> None:
    with pytest.raises(
        ValueError, match="destination_urls are only supported if the Firewall SKU is Premium"
    ):
        FirewallConfig.model_validate(
            {
                "sku": "Standard",
                "subnet": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/test/providers/Microsoft.Network/virtualNetworks/vnet/subnets/AzureFirewallSubnet",
                "rule_collection_groups": [
                    {
                        "name": "group1",
                        "priority": 100,
                        "rule_collections": [
                            {
                                "name": "collection1",
                                "type": "Application",
                                "priority": 200,
                                "action": "Allow",
                                "rules": [
                                    {
                                        "name": "rule1",
                                        "source_ip_addresses": "10.0.0.0/24",
                                        "destination_urls": ["https://example.com/*"],
                                        "protocols": [{"protocol": "Https"}],
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        )


def test_firewall_config_duplicate_group_priorities() -> None:
    with pytest.raises(ValueError, match="Duplicate priority .* found in Rule Collection Groups"):
        FirewallConfig.model_validate(
            {
                "sku": "Standard",
                "subnet": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/test/providers/Microsoft.Network/virtualNetworks/vnet/subnets/AzureFirewallSubnet",
                "rule_collection_groups": [
                    {
                        "name": "group1",
                        "priority": 100,
                        "rule_collections": [
                            {
                                "name": "collection1",
                                "type": "Network",
                                "priority": 200,
                                "action": "Allow",
                                "rules": [],
                            }
                        ],
                    },
                    {
                        "name": "group2",
                        "priority": 100,  # Duplicate!
                        "rule_collections": [
                            {
                                "name": "collection2",
                                "type": "Network",
                                "priority": 300,
                                "action": "Allow",
                                "rules": [],
                            }
                        ],
                    },
                ],
            }
        )


def test_firewall_config_duplicate_collection_priorities() -> None:
    with pytest.raises(
        ValueError,
        match="Duplicate priority .* found in RuleCollections within RuleCollectionGroup",
    ):
        FirewallConfig.model_validate(
            {
                "sku": "Standard",
                "subnet": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/test/providers/Microsoft.Network/virtualNetworks/vnet/subnets/AzureFirewallSubnet",
                "rule_collection_groups": [
                    {
                        "name": "group1",
                        "priority": 100,
                        "rule_collections": [
                            {
                                "name": "collection1",
                                "type": "Network",
                                "priority": 200,
                                "action": "Allow",
                                "rules": [],
                            },
                            {
                                "name": "collection2",
                                "type": "Network",
                                "priority": 200,  # Duplicate!
                                "action": "Allow",
                                "rules": [],
                            },
                        ],
                    }
                ],
            }
        )


def test_firewall_config_valid_standard() -> None:
    config = FirewallConfig.model_validate(
        {
            "sku": "Standard",
            "subnet": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/test/providers/Microsoft.Network/virtualNetworks/vnet/subnets/AzureFirewallSubnet",
            "dns_proxy": True,
        }
    )
    assert config.sku == "Standard"
    assert config.dns_proxy is True

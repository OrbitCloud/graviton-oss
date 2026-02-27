"""
Phase 1: Pre-migration snapshot tests for resource metadata.

These tests lock down the exact current behavior of both v1 (RESOURCE_PREFIXES / naming_v1)
and v2 (_azure_resource_meta / meta.py) systems. They serve as a safety net: if any prefix,
naming rule, or metadata value changes during migration, these tests will fail.

Created as part of the yaml-resource-metadata Phase 1 requirements.
"""

from __future__ import annotations

import inspect
from typing import Any

import pydantic
import pytest
from pulumi_azure_native import (
    app,
    appconfiguration,
    authorization,
    cognitiveservices,
    containerregistry,
    eventgrid,
    eventhub,
    keyvault,
    network,
    operationalinsights,
    providerhub,
    resources,
    search,
    servicebus,
    sql,
    storage,
    web,
)

from orbitcloud_graviton.az_lib.helpers import location_abbr
from orbitcloud_graviton.az_lib.meta import (
    AzureResourceMetadata,
    resource_meta,
)
from orbitcloud_graviton.az_lib.metadata.loader import (
    RESOURCE_PREFIXES,
    _azure_regions,
    _azure_resource_meta,
)
from orbitcloud_graviton.az_lib.naming import ResourceNameRule
from orbitcloud_graviton.az_lib.naming_v1 import get_prefix, resource_namer
from orbitcloud_graviton.pulumi_lib.azure_base import AzureStack

# ---------------------------------------------------------------------------
# 1. Snapshot test for all v1 prefixes
# ---------------------------------------------------------------------------

# Expected snapshot of every entry in RESOURCE_PREFIXES.
# Keys: prefix, alphanumeric (default False), lowercase (default False), max_length (default None).
V1_PREFIX_SNAPSHOT: dict[str, dict[str, Any]] = {
    "pulumi_azure_native.resources.resource_group": {"prefix": "rg"},
    "pulumi_azure_native.operationalinsights.workspace": {"prefix": "log"},
    "pulumi_azure_native.containerregistry.registry": {"prefix": "cr", "alphanumeric": True},
    "pulumi_azure_native.monitor.diagnostic_setting": {"prefix": "diag"},
    "pulumi_azure_native.web.app_service_plan": {"prefix": "asp"},
    "pulumi_azure_native.web.app_service": {"prefix": "app"},
    "pulumi_azure_native.keyvault.vault": {
        "prefix": "kv",
        "alphanumeric": True,
        "max_length": 24,
    },
    "pulumi_azure_native.storage.storage_account": {
        "prefix": "st",
        "alphanumeric": True,
        "lowercase": True,
    },
    "pulumi_azure_native.network.private_dns_zone_group": {"prefix": "pdzg"},
    "pulumi_azure_native.app.managed_environment": {"prefix": "cae", "max_length": 60},
    "pulumi_azure_native.network.virtual_network": {"prefix": "vnet"},
    "pulumi_azure_native.network.subnet": {"prefix": "snet"},
    "pulumi_azure_native.network.virtual_wan": {"prefix": "vwan"},
    "pulumi_azure_native.network.virtual_hub": {"prefix": "vhub"},
    "pulumi_azure_native.network.vpn_server_configuration": {"prefix": "vpnconf"},
    "pulumi_azure_native.network.p2s_vpn_gateway": {"prefix": "vpng"},
    "pulumi_azure_native.network.hub_virtual_network_connection": {"prefix": "vhubc"},
    "pulumi_azure_native.network.route_table": {"prefix": "rt"},
    "pulumi_azure_native.eventhub.namespace": {"prefix": "evhns"},
    "pulumi_azure_native.eventhub.event_hub": {"prefix": "evh"},
    "pulumi_azure_native.eventhub.namespace_authorization_rule": {"prefix": "evhns-key"},
    "pulumi_azure_native.eventhub.namespace_network_rule_set": {"prefix": "evhns-nwrule"},
    "pulumi_azure_native.storage.table": {"prefix": "sttbl"},
    "pulumi_azure_native.storage.blob_container": {"prefix": "stctr"},
    "pulumi_azure_native.storage.queue": {"prefix": "stq"},
    "pulumi_azure_native.storage.file_share": {"prefix": "stfs"},
    "pulumi_azure_native.storage.file_service_properties": {"prefix": "stfsp"},
    "pulumi_azure_native.providerhub.provider_registration": {"prefix": "proreg"},
    "pulumi_azure_native.providerhub.resource_type_registration": {"prefix": "prov"},
    "pulumi_azure_native.keyvault.secret": {"prefix": "kvs"},
    "pulumi_azure_native.app.container_app": {"prefix": "app"},
    "pulumi_azure_native.app.managed_certificate": {"prefix": "cert"},
    "pulumi_azure_native.app.certificate": {"prefix": "caecert-"},
    "pulumi_azure_native.app.app_resiliency": {"prefix": "appres"},
    "pulumi_azure_native.applicationinsights.component": {"prefix": "appi"},
    "pulumi_azure_native.dns.zone": {"prefix": "dns"},
    "pulumi_azure_native.dns.record_set": {"prefix": "dnsr"},
    "pulumi_azure_native.privatedns.private_record_set": {"prefix": "dnsr"},
    "pulumi_azure_native.network.vpn_gateway": {"prefix": "vpng"},
    "pulumi_azure_native.network.virtual_network_gateway": {"prefix": "vgw"},
    "pulumi_azure_native.network.virtual_network_gateway_connection": {"prefix": "con"},
    "pulumi_azure_native.network.local_network_gateway": {"prefix": "lgw"},
    "pulumi_azure_native.dnsresolver.dns_resolver": {"prefix": "dnspr"},
    "pulumi_azure_native.dnsresolver.inbound_endpoint": {"prefix": "in"},
    "pulumi_azure_native.dnsresolver.outbound_endpoint": {"prefix": "out"},
    "pulumi_azure_native.dnsresolver.dns_forwarding_ruleset": {"prefix": "dnsfrs"},
    "pulumi_azure_native.authorization.role_assignment": {"prefix": "iam"},
    "pulumi_azure_native.managedidentity.user_assigned_identity": {"prefix": "id"},
    "pulumi_azure_native.appconfiguration.configuration_store": {"prefix": "appcs"},
    "pulumi_azure_native.appconfiguration.key_value": {"prefix": "appcsk"},
    "pulumi_azure_native.eventgrid.domain": {"prefix": "evgd"},
    "pulumi_azure_native.eventgrid.domain_topic": {"prefix": "evgt"},
    "pulumi_azure_native.network.private_endpoint": {"prefix": "pep"},
    "pulumi_azure_native.search.service": {"prefix": "srch"},
    "pulumi_azure_native.cognitiveservices.account": {"prefix": "oai"},
    "pulumi_azure_native.dbforpostgresql.server": {"prefix": "psql"},
    "pulumi_azure_native.dbforpostgresql.administrator": {"prefix": "psql-admin"},
    "pulumi_azure_native.dbforpostgresql.configuration": {"prefix": "psql-conf"},
    "pulumi_azure_native.servicebus.namespace": {"prefix": "sbns"},
    "pulumi_azure_native.servicebus.queue": {"prefix": "sbq"},
    "pulumi_azure_native.servicebus.topic": {"prefix": "sbt"},
    "pulumi_azure_native.servicebus.namespace_network_rule_set": {"prefix": "sbns-nwrule"},
    "pulumi_azure_native.servicebus.namespace_ip_filter_rule": {"prefix": "sbns-iprule"},
    "pulumi_azure_native.sql.database": {"prefix": "sqldb"},
    "pulumi_azure_native.sql.server": {"prefix": "sql"},
    "pulumi_azure_native.sql.elastic_pool": {"prefix": "sqlep"},
    "pulumi_azure_native.sql.firewall_rule": {"prefix": "sqlfw"},
    "pulumi_azure_native.sql.server_dns_alias": {"prefix": "sqldns"},
    "pulumi_azure_native.sql.job_agent": {"prefix": "sqlja"},
    "pulumi_azure_native.sql.job_target_group": {"prefix": "sqljtg"},
    "pulumi_azure_native.sql.job": {"prefix": "sqljob"},
    "pulumi_azure_native.sql.job_step": {"prefix": "sqljs"},
    "pulumi_random.random_password": {"prefix": "rand"},
    "pulumi_azure_native.compute.virtual_machine": {"prefix": "vm"},
    "pulumi_azure_native.compute.disk": {"prefix": "disk"},
    "pulumi_azure_native.network.network_interface": {"prefix": "nic"},
    "pulumi_azure_native.network.azure_firewall": {"prefix": "azfw"},
    "pulumi_azure_native.network.firewall_policy": {"prefix": "azfwp"},
    "pulumi_azure_native.network.dnssec_config": {"prefix": "dnssec"},
    "pulumi_azure_native.recoveryservices.vault": {"prefix": "rsv"},
    "pulumi_azure_native.recoveryservices.protection_policy": {"prefix": "rsvpp"},
}


@pytest.mark.parametrize(
    "module_path",
    sorted(RESOURCE_PREFIXES.keys()),
    ids=lambda p: p.split(".")[-1],
)
def test_v1_prefix_snapshot(module_path: str) -> None:
    """Each v1 prefix entry must exactly match the snapshot."""
    actual = RESOURCE_PREFIXES[module_path]
    expected = V1_PREFIX_SNAPSHOT[module_path]
    assert actual == expected, (
        f"V1 prefix mismatch for {module_path}: expected {expected}, got {actual}"
    )


def test_v1_prefix_count() -> None:
    """The number of entries in RESOURCE_PREFIXES must match the snapshot exactly."""
    assert len(RESOURCE_PREFIXES) == len(V1_PREFIX_SNAPSHOT), (
        f"RESOURCE_PREFIXES has {len(RESOURCE_PREFIXES)} entries, "
        f"snapshot has {len(V1_PREFIX_SNAPSHOT)}"
    )


def test_v1_snapshot_keys_match_source() -> None:
    """All keys in the snapshot must exist in RESOURCE_PREFIXES and vice versa."""
    snapshot_keys = set(V1_PREFIX_SNAPSHOT.keys())
    source_keys = set(RESOURCE_PREFIXES.keys())
    assert snapshot_keys == source_keys, (
        f"Key mismatch.\n"
        f"  In snapshot only: {snapshot_keys - source_keys}\n"
        f"  In source only: {source_keys - snapshot_keys}"
    )


# ---------------------------------------------------------------------------
# 2. Snapshot test for all v2 metadata
# ---------------------------------------------------------------------------

# Expected snapshot of every resource in _azure_resource_meta.
# Structure: {namespace: {class_name: {full metadata dict}}}
V2_METADATA_SNAPSHOT: dict[str, Any] = {
    "app": {
        "namespace": "Microsoft.App",
        "resources": {
            "ContainerApp": {
                "naming": {"prefix": "app"},
            },
            "Certificate": {
                "naming": {"prefix": "caecert-"},
            },
            "ManagedCertificate": {
                "naming": {"prefix": "cert"},
            },
            "ManagedEnvironment": {
                "naming": {"prefix": "cae", "max_length": 60},
            },
            "AppResiliency": {
                "naming": {"prefix": "appres"},
            },
        },
    },
    "appconfiguration": {
        "namespace": "Microsoft.AppConfiguration",
        "resources": {
            "ConfigurationStore": {
                "naming": {"prefix": "appcs"},
                "namespace": "Microsoft.AppConfiguration/configurationStores",
                "sub_resource_name": "configurationStore",
                "public_dns_zone": "azconfig.io",
                "private_dns_zone": "privatelink.azconfig.io",
            },
            "KeyValue": {
                "naming": {"prefix": "appcsk"},
            },
        },
    },
    "authorization": {
        "namespace": "Microsoft.Authorization",
        "resources": {
            "RoleAssignment": {
                "naming": {"prefix": "iam"},
            },
        },
    },
    "cognitiveservices": {
        "namespace": "Microsoft.CognitiveServices",
        "resources": {
            "Account": {
                "naming": {"prefix": "oai"},
                "sub_resource_name": "account",
                "private_dns_zone": "privatelink.openai.azure.com",
            },
        },
    },
    "containerregistry": {
        "namespace": "Microsoft.ContainerRegistry",
        "resources": {
            "Registry": {
                "naming": {"prefix": "cr", "alphanumeric": True},
                "namespace": "Microsoft.ContainerRegistry/registries",
                "sub_resource_name": "registry",
                "public_dns_zone": "azurecr.io",
                "private_dns_zone": "privatelink.azurecr.io",
            },
        },
    },
    "eventgrid": {
        "namespace": "Microsoft.EventGrid",
        "resources": {
            "Domain": {
                "naming": {"prefix": "evgd"},
                "namespace": "Microsoft.EventGrid/domains",
                "sub_resource_name": "domain",
                "private_dns_zone": "privatelink.eventgrid.azure.net",
            },
            "DomainTopic": {
                "naming": {"prefix": "evgt"},
                "namespace": "Microsoft.EventGrid/topics",
                "sub_resource_name": "topic",
                "private_dns_zone": "privatelink.eventgrid.azure.net",
            },
        },
    },
    "eventhub": {
        "namespace": "Microsoft.EventHub",
        "resources": {
            "Namespace": {
                "naming": {"prefix": "evhns"},
                "namespace": "Microsoft.EventHub/namespaces",
                "sub_resource_name": "namespace",
                "private_dns_zone": "privatelink.servicebus.windows.net",
            },
            "Eventhub": {
                "naming": {"prefix": "evh"},
            },
            "EventHub": {
                "naming": {"prefix": "evh"},
            },
            "NamespaceAuthorizationRule": {
                "naming": {"prefix": "evhns-key"},
            },
            "NamespaceNetworkRuleSet": {
                "naming": {"prefix": "evhns-nwrule"},
            },
        },
    },
    "insights": {
        "namespace": "Microsoft.Insights",
        "resources": {
            "Component": {
                "naming": {"prefix": "appi"},
            },
            "Diagnosticsetting": {
                "naming": {"prefix": "diag"},
            },
            "DiagnosticSetting": {
                "naming": {"prefix": "diag"},
            },
        },
    },
    "keyvault": {
        "namespace": "Microsoft.KeyVault",
        "resources": {
            "Vault": {
                "naming": {"prefix": "kv", "alphanumeric": True, "max_length": 24},
                "namespace": "Microsoft.KeyVault/vaults",
                "sub_resource_name": "vault",
                "public_dns_zone": "vault.azure.net",
                "private_dns_zone": "privatelink.vaultcore.azure.net",
            },
            "Secret": {
                "naming": {"prefix": "kvs"},
            },
        },
    },
    "network": {
        "namespace": "Microsoft.Network",
        "resources": {
            "VirtualNetwork": {
                "naming": {"prefix": "vnet"},
                "namespace": "Microsoft.Network/virtualNetworks",
            },
            "PrivateDnsZoneGroup": {
                "naming": {"prefix": "pdzg"},
                "namespace": "Microsoft.Network/privateDnsZoneGroups",
            },
            "Subnet": {
                "naming": {"prefix": "snet"},
                "namespace": "Microsoft.Network/virtualNetworks/subnets",
                "sub_resource_name": "subnet",
            },
            "VirtualWan": {
                "naming": {"prefix": "vwan"},
            },
            "VirtualHub": {
                "naming": {"prefix": "vhub"},
            },
            "VpnServerConfiguration": {
                "naming": {"prefix": "vpnconf"},
            },
            "P2sVpnGateway": {
                "naming": {"prefix": "vpng"},
            },
            "HubVirtualNetworkConnection": {
                "naming": {"prefix": "vhubc"},
            },
            "VpnGateway": {
                "naming": {"prefix": "vpng"},
            },
            "VirtualNetworkGateway": {
                "naming": {"prefix": "vgw"},
            },
            "VirtualNetworkGatewayConnection": {
                "naming": {"prefix": "con"},
            },
            "LocalNetworkGateway": {
                "naming": {"prefix": "lgw"},
            },
            "PrivateEndpoint": {
                "naming": {"prefix": "pep"},
            },
            "RouteTable": {
                "naming": {"prefix": "rt"},
            },
            "NetworkInterface": {
                "naming": {"prefix": "nic"},
            },
            "AzureFirewall": {
                "naming": {"prefix": "azfw"},
            },
            "FirewallPolicy": {
                "naming": {"prefix": "azfwp"},
            },
            "DnssecConfig": {
                "naming": {"prefix": "dnssec"},
            },
        },
    },
    "operationalinsights": {
        "namespace": "Microsoft.OperationalInsights",
        "resources": {
            "Workspace": {
                "naming": {"prefix": "log"},
            },
        },
    },
    "providerhub": {
        # Note: no "namespace" key at the service level
        "resources": {
            "ProviderRegistration": {
                "naming": {"prefix": "proreg"},
            },
            "ResourceTypeRegistration": {
                "naming": {"prefix": "prov"},
            },
        },
    },
    "resources": {
        "namespace": "Microsoft.Resources",
        "resources": {
            "ResourceGroup": {
                "namespace": "Microsoft.Resources/resourceGroups",
                "resource_type": "resourceGroup",
                "naming": {"prefix": "rg"},
            },
        },
    },
    "servicebus": {
        "namespace": "Microsoft.ServiceBus",
        "resources": {
            "Namespace": {
                "naming": {"prefix": "sbns"},
                "namespace": "Microsoft.ServiceBus/namespaces",
                "sub_resource_name": "namespace",
                "private_dns_zone": "privatelink.servicebus.windows.net",
            },
            "Queue": {
                "naming": {"prefix": "sbq"},
            },
            "Topic": {
                "naming": {"prefix": "sbt"},
            },
            "NamespaceNetworkRuleSet": {
                "naming": {"prefix": "sbns-nwrule"},
            },
            "NamespaceIpFilterRule": {
                "naming": {"prefix": "sbns-iprule"},
            },
        },
    },
    "sql": {
        "namespace": "Microsoft.Sql",
        "resources": {
            "Database": {
                "naming": {"prefix": "sqldb"},
                "namespace": "Microsoft.Sql/servers/databases",
                "resource_type": "servers/databases",
                "private_dns_zone": "privatelink.database.windows.net",
                "public_dns_zone": "database.windows.net",
            },
            "Server": {
                "naming": {"prefix": "sql"},
                "namespace": "Microsoft.Sql/servers",
                "sub_resource_name": "sqlServer",
                "private_dns_zone": "privatelink.database.windows.net",
                "public_dns_zone": "database.windows.net",
            },
            "FirewallRule": {
                "naming": {"prefix": "sqlfw"},
            },
            "ServerDnsAlias": {
                "naming": {"prefix": "sqldns"},
            },
            "ElasticPool": {
                "naming": {"prefix": "sqlep"},
            },
            "JobAgent": {
                "naming": {"prefix": "sqlja"},
            },
            "JobTargetGroup": {
                "naming": {"prefix": "sqljtg"},
            },
            "Job": {
                "naming": {"prefix": "sqljob"},
            },
            "JobStep": {
                "naming": {"prefix": "sqljs"},
            },
        },
    },
    "search": {
        "namespace": "Microsoft.Search",
        "resources": {
            "Service": {
                "namespace": "Microsoft.Search/searchServices",
                "resource_type": "searchServices",
                "sub_resource_name": "searchService",
                "naming": {"prefix": "srch"},
                "public_dns_zone": "search.windows.net",
                "private_dns_zone": "privatelink.search.windows.net",
            },
        },
    },
    "storage": {
        "namespace": "Microsoft.Storage",
        "resources": {
            "StorageAccount": {
                "naming": {"prefix": "st", "alphanumeric": True, "lowercase": True},
                "namespace": "Microsoft.Storage/storageAccounts",
                "resource_type": "Microsoft.Storage/storageAccounts/storageAccount",
            },
            "Table": {
                "naming": {"prefix": "sttbl"},
                "namespace": "Microsoft.Storage/storageAccounts/tableServices",
                "resource_type": "storageAccounts/tableServices/tables",
                "sub_resource_name": "table",
                "private_dns_zone": "privatelink.table.core.windows.net",
            },
            "Queue": {
                "naming": {"prefix": "stq"},
                "namespace": "Microsoft.Storage/storageAccounts/queueServices",
                "resource_type": "storageAccounts/queueServices/queues",
                "sub_resource_name": "queue",
                "private_dns_zone": "privatelink.queue.core.windows.net",
            },
            "BlobContainer": {
                "naming": {"prefix": "stctr"},
                "namespace": "Microsoft.Storage/storageAccounts/blobServices",
                "resource_type": "storageAccounts/blobServices/containers",
                "sub_resource_name": "blob",
                "private_dns_zone": "privatelink.blob.core.windows.net",
            },
            "FileShare": {
                "naming": {"prefix": "stfs"},
                "namespace": "Microsoft.Storage/storageAccounts/fileServices",
                "resource_type": "storageAccounts/fileServices/shares",
                "sub_resource_name": "file",
                "private_dns_zone": "privatelink.file.core.windows.net",
            },
            "FileServiceProperties": {
                "naming": {"prefix": "stfsp"},
            },
        },
    },
    "web": {
        "namespace": "Microsoft.Web",
        "resources": {
            "AppServicePlan": {
                "naming": {"prefix": "asp"},
            },
            "WebApp": {
                "naming": {"prefix": "app"},
                "namespace": "Microsoft.Web/sites",
                "sub_resource_name": "site",
                "public_dns_zone": "azurewebsites.net",
                "private_dns_zone": "privatelink.azurewebsites.net",
            },
        },
    },
}


def _collect_v2_resource_params() -> list[tuple[str, str, dict[str, Any]]]:
    """Collect all (namespace, class_name, metadata) from _azure_resource_meta."""
    params = []
    for ns_key, ns_data in _azure_resource_meta["pulumi_azure_native"].items():
        for class_name, resource_data in ns_data["resources"].items():
            params.append((ns_key, class_name, resource_data))
    return params


@pytest.mark.parametrize(
    ("ns_key", "class_name", "resource_data"),
    _collect_v2_resource_params(),
    ids=lambda p: p if isinstance(p, str) else "",
)
def test_v2_metadata_snapshot(ns_key: str, class_name: str, resource_data: dict[str, Any]) -> None:
    """Each v2 metadata entry must exactly match the snapshot."""
    expected_ns = V2_METADATA_SNAPSHOT[ns_key]
    expected_resource = expected_ns["resources"][class_name]
    assert resource_data == expected_resource, (
        f"V2 metadata mismatch for {ns_key}.{class_name}:\n"
        f"  expected: {expected_resource}\n"
        f"  actual:   {resource_data}"
    )


def test_v2_namespace_count() -> None:
    """The number of service namespaces in _azure_resource_meta must match the snapshot."""
    actual_namespaces = set(_azure_resource_meta["pulumi_azure_native"].keys())
    expected_namespaces = set(V2_METADATA_SNAPSHOT.keys())
    assert actual_namespaces == expected_namespaces, (
        f"Namespace mismatch.\n"
        f"  In source only: {actual_namespaces - expected_namespaces}\n"
        f"  In snapshot only: {expected_namespaces - actual_namespaces}"
    )


def test_v2_service_level_metadata_snapshot() -> None:
    """Service-level metadata (namespace field) must match the snapshot."""
    for ns_key, ns_data in _azure_resource_meta["pulumi_azure_native"].items():
        expected = V2_METADATA_SNAPSHOT[ns_key]
        # Compare all keys except "resources"
        for key in ns_data:
            if key == "resources":
                continue
            assert ns_data[key] == expected.get(key), (
                f"Service-level metadata mismatch for {ns_key}.{key}: "
                f"expected {expected.get(key)!r}, got {ns_data[key]!r}"
            )


def test_v2_resource_count_per_namespace() -> None:
    """Each namespace must have the same number of resource entries as the snapshot."""
    for ns_key, ns_data in _azure_resource_meta["pulumi_azure_native"].items():
        actual_resources = set(ns_data["resources"].keys())
        expected_resources = set(V2_METADATA_SNAPSHOT[ns_key]["resources"].keys())
        assert actual_resources == expected_resources, (
            f"Resource mismatch in namespace {ns_key}.\n"
            f"  In source only: {actual_resources - expected_resources}\n"
            f"  In snapshot only: {expected_resources - actual_resources}"
        )


# ---------------------------------------------------------------------------
# 3. Snapshot test for all regions
# ---------------------------------------------------------------------------

REGIONS_SNAPSHOT: dict[str, dict[str, str]] = {
    "northeurope": {"name": "North Europe", "abbr": "neu"},
    "westeurope": {"name": "West Europe", "abbr": "weu"},
    "swedencentral": {"name": "Sweden Central", "abbr": "swe"},
    "norwayeast": {"name": "Norway East", "abbr": "noe"},
    "norwaywest": {"name": "Norway West", "abbr": "now"},
}


@pytest.mark.parametrize(
    "region_key",
    sorted(_azure_regions.keys()),
)
def test_region_snapshot(region_key: str) -> None:
    """Each region entry must exactly match the snapshot."""
    actual = _azure_regions[region_key]
    expected = REGIONS_SNAPSHOT[region_key]
    assert actual == expected, (
        f"Region mismatch for {region_key}: expected {expected}, got {actual}"
    )


def test_region_count() -> None:
    """The number of regions must match the snapshot exactly."""
    assert set(_azure_regions.keys()) == set(REGIONS_SNAPSHOT.keys())


def test_location_abbr_function_matches_regions() -> None:
    """location_abbr() must return the correct abbreviation for all known regions."""
    for region_key, region_data in _azure_regions.items():
        assert location_abbr(region_key) == region_data["abbr"], (
            f"location_abbr({region_key!r}) returned {location_abbr(region_key)!r}, "
            f"expected {region_data['abbr']!r}"
        )


# ---------------------------------------------------------------------------
# 4. End-to-end naming tests for every resource type via v1 API
# ---------------------------------------------------------------------------

# Build a mapping from module_path to the actual Pulumi class for v1 testing.
# We need the class objects to pass to resource_namer() which calls get_prefix().
# Some classes don't exist in the current SDK version (e.g., DnssecConfig was removed,
# web.AppService is actually web.WebApp). We use a mock class approach.


class _MockPulumiClass:
    """A minimal mock that has __module__ set to simulate a Pulumi resource class."""

    def __init__(self, module_path: str) -> None:
        self.__module__ = module_path


# Fixed inputs for v1 naming tests
_V1_WORKLOAD = "workload"
_V1_ENV = "test"
_V1_LOCATION = "northeurope"
_V1_INSTANCE = "01"

# Expected v1 naming output for every resource type.
# Generated using the formula: {prefix}{sep}{workload}{sep}{env}{sep}{location_abbr}{sep}{instance}
# Where sep="-" normally, sep="" if alphanumeric, and result is lowered if lowercase=True.
V1_NAMING_EXPECTED: dict[str, str] = {
    "pulumi_azure_native.resources.resource_group": "rg-workload-test-neu-01",
    "pulumi_azure_native.operationalinsights.workspace": "log-workload-test-neu-01",
    "pulumi_azure_native.containerregistry.registry": "CrWorkloadTestNeu01",
    "pulumi_azure_native.monitor.diagnostic_setting": "diag-workload-test-neu-01",
    "pulumi_azure_native.web.app_service_plan": "asp-workload-test-neu-01",
    "pulumi_azure_native.web.app_service": "app-workload-test-neu-01",
    "pulumi_azure_native.keyvault.vault": "KvWorkloadTestNeu01",
    "pulumi_azure_native.storage.storage_account": "stworkloadtestneu01",
    "pulumi_azure_native.network.private_dns_zone_group": "pdzg-workload-test-neu-01",
    "pulumi_azure_native.app.managed_environment": "cae-workload-test-neu-01",
    "pulumi_azure_native.network.virtual_network": "vnet-workload-test-neu-01",
    "pulumi_azure_native.network.subnet": "snet-workload-test-neu-01",
    "pulumi_azure_native.network.virtual_wan": "vwan-workload-test-neu-01",
    "pulumi_azure_native.network.virtual_hub": "vhub-workload-test-neu-01",
    "pulumi_azure_native.network.vpn_server_configuration": "vpnconf-workload-test-neu-01",
    "pulumi_azure_native.network.p2s_vpn_gateway": "vpng-workload-test-neu-01",
    "pulumi_azure_native.network.hub_virtual_network_connection": "vhubc-workload-test-neu-01",
    "pulumi_azure_native.network.route_table": "rt-workload-test-neu-01",
    "pulumi_azure_native.eventhub.namespace": "evhns-workload-test-neu-01",
    "pulumi_azure_native.eventhub.event_hub": "evh-workload-test-neu-01",
    "pulumi_azure_native.eventhub.namespace_authorization_rule": "evhns-key-workload-test-neu-01",
    "pulumi_azure_native.eventhub.namespace_network_rule_set": "evhns-nwrule-workload-test-neu-01",
    "pulumi_azure_native.storage.table": "sttbl-workload-test-neu-01",
    "pulumi_azure_native.storage.blob_container": "stctr-workload-test-neu-01",
    "pulumi_azure_native.storage.queue": "stq-workload-test-neu-01",
    "pulumi_azure_native.storage.file_share": "stfs-workload-test-neu-01",
    "pulumi_azure_native.storage.file_service_properties": "stfsp-workload-test-neu-01",
    "pulumi_azure_native.providerhub.provider_registration": "proreg-workload-test-neu-01",
    "pulumi_azure_native.providerhub.resource_type_registration": "prov-workload-test-neu-01",
    "pulumi_azure_native.keyvault.secret": "kvs-workload-test-neu-01",
    "pulumi_azure_native.app.container_app": "app-workload-test-neu-01",
    "pulumi_azure_native.app.managed_certificate": "cert-workload-test-neu-01",
    "pulumi_azure_native.app.certificate": "caecert--workload-test-neu-01",
    "pulumi_azure_native.app.app_resiliency": "appres-workload-test-neu-01",
    "pulumi_azure_native.applicationinsights.component": "appi-workload-test-neu-01",
    "pulumi_azure_native.dns.zone": "dns-workload-test-neu-01",
    "pulumi_azure_native.dns.record_set": "dnsr-workload-test-neu-01",
    "pulumi_azure_native.privatedns.private_record_set": "dnsr-workload-test-neu-01",
    "pulumi_azure_native.network.vpn_gateway": "vpng-workload-test-neu-01",
    "pulumi_azure_native.network.virtual_network_gateway": "vgw-workload-test-neu-01",
    "pulumi_azure_native.network.virtual_network_gateway_connection": "con-workload-test-neu-01",
    "pulumi_azure_native.network.local_network_gateway": "lgw-workload-test-neu-01",
    "pulumi_azure_native.dnsresolver.dns_resolver": "dnspr-workload-test-neu-01",
    "pulumi_azure_native.dnsresolver.inbound_endpoint": "in-workload-test-neu-01",
    "pulumi_azure_native.dnsresolver.outbound_endpoint": "out-workload-test-neu-01",
    "pulumi_azure_native.dnsresolver.dns_forwarding_ruleset": "dnsfrs-workload-test-neu-01",
    "pulumi_azure_native.authorization.role_assignment": "iam-workload-test-neu-01",
    "pulumi_azure_native.managedidentity.user_assigned_identity": "id-workload-test-neu-01",
    "pulumi_azure_native.appconfiguration.configuration_store": "appcs-workload-test-neu-01",
    "pulumi_azure_native.appconfiguration.key_value": "appcsk-workload-test-neu-01",
    "pulumi_azure_native.eventgrid.domain": "evgd-workload-test-neu-01",
    "pulumi_azure_native.eventgrid.domain_topic": "evgt-workload-test-neu-01",
    "pulumi_azure_native.network.private_endpoint": "pep-workload-test-neu-01",
    "pulumi_azure_native.search.service": "srch-workload-test-neu-01",
    "pulumi_azure_native.cognitiveservices.account": "oai-workload-test-neu-01",
    "pulumi_azure_native.dbforpostgresql.server": "psql-workload-test-neu-01",
    "pulumi_azure_native.dbforpostgresql.administrator": "psql-admin-workload-test-neu-01",
    "pulumi_azure_native.dbforpostgresql.configuration": "psql-conf-workload-test-neu-01",
    "pulumi_azure_native.servicebus.namespace": "sbns-workload-test-neu-01",
    "pulumi_azure_native.servicebus.queue": "sbq-workload-test-neu-01",
    "pulumi_azure_native.servicebus.topic": "sbt-workload-test-neu-01",
    "pulumi_azure_native.servicebus.namespace_network_rule_set": "sbns-nwrule-workload-test-neu-01",
    "pulumi_azure_native.servicebus.namespace_ip_filter_rule": "sbns-iprule-workload-test-neu-01",
    "pulumi_azure_native.sql.database": "sqldb-workload-test-neu-01",
    "pulumi_azure_native.sql.server": "sql-workload-test-neu-01",
    "pulumi_azure_native.sql.elastic_pool": "sqlep-workload-test-neu-01",
    "pulumi_azure_native.sql.firewall_rule": "sqlfw-workload-test-neu-01",
    "pulumi_azure_native.sql.server_dns_alias": "sqldns-workload-test-neu-01",
    "pulumi_azure_native.sql.job_agent": "sqlja-workload-test-neu-01",
    "pulumi_azure_native.sql.job_target_group": "sqljtg-workload-test-neu-01",
    "pulumi_azure_native.sql.job": "sqljob-workload-test-neu-01",
    "pulumi_azure_native.sql.job_step": "sqljs-workload-test-neu-01",
    "pulumi_random.random_password": "rand-workload-test-neu-01",
    "pulumi_azure_native.compute.virtual_machine": "vm-workload-test-neu-01",
    "pulumi_azure_native.compute.disk": "disk-workload-test-neu-01",
    "pulumi_azure_native.network.network_interface": "nic-workload-test-neu-01",
    "pulumi_azure_native.network.azure_firewall": "azfw-workload-test-neu-01",
    "pulumi_azure_native.network.firewall_policy": "azfwp-workload-test-neu-01",
    "pulumi_azure_native.network.dnssec_config": "dnssec-workload-test-neu-01",
    "pulumi_azure_native.recoveryservices.vault": "rsv-workload-test-neu-01",
    "pulumi_azure_native.recoveryservices.protection_policy": "rsvpp-workload-test-neu-01",
}


@pytest.mark.parametrize(
    "module_path",
    sorted(RESOURCE_PREFIXES.keys()),
    ids=lambda p: p.split(".")[-1],
)
def test_v1_naming_end_to_end(module_path: str) -> None:
    """resource_namer() must produce the exact expected name for each resource type."""
    mock_class = _MockPulumiClass(module_path)
    result = resource_namer(
        resource_type=mock_class,
        workload_name=_V1_WORKLOAD,
        env=_V1_ENV,
        location=_V1_LOCATION,
        instance_number=_V1_INSTANCE,
    )
    expected = V1_NAMING_EXPECTED[module_path]
    assert result == expected, (
        f"V1 naming mismatch for {module_path}: expected {expected!r}, got {result!r}"
    )


def test_v1_naming_expected_count() -> None:
    """All resource types must have an expected naming result."""
    assert set(V1_NAMING_EXPECTED.keys()) == set(RESOURCE_PREFIXES.keys())


# ---------------------------------------------------------------------------
# 5. End-to-end naming tests for every resource type via v2 API
# ---------------------------------------------------------------------------

# Mapping from (v2_namespace, v2_class_name) -> actual Pulumi class.
# Some v2 entries cannot be resolved via resource_meta() due to namespace mismatches
# or the missing "naming" wrapper (AppServicePlan). These are documented and skipped.
_V2_PULUMI_CLASSES: dict[tuple[str, str], type | None] = {
    # app
    ("app", "ContainerApp"): app.ContainerApp,
    ("app", "Certificate"): app.Certificate,
    ("app", "ManagedEnvironment"): app.ManagedEnvironment,
    # appconfiguration
    ("appconfiguration", "ConfigurationStore"): appconfiguration.ConfigurationStore,
    ("appconfiguration", "KeyValue"): appconfiguration.KeyValue,
    # authorization
    ("authorization", "RoleAssignment"): authorization.RoleAssignment,
    # cognitiveservices
    ("cognitiveservices", "Account"): cognitiveservices.Account,
    # containerregistry
    ("containerregistry", "Registry"): containerregistry.Registry,
    # eventgrid
    ("eventgrid", "Domain"): eventgrid.Domain,
    ("eventgrid", "DomainTopic"): eventgrid.DomainTopic,
    # eventhub
    ("eventhub", "Namespace"): eventhub.Namespace,
    ("eventhub", "Eventhub"): None,  # Class is EventHub, but v2 key is "Eventhub" -> KeyError
    ("eventhub", "NamespaceAuthorizationRule"): eventhub.NamespaceAuthorizationRule,
    # insights - Pulumi module is "applicationinsights"/"monitor", not "insights"
    ("insights", "Component"): None,  # applicationinsights.Component -> namespace mismatch
    ("insights", "Diagnosticsetting"): None,  # monitor.DiagnosticSetting -> namespace mismatch
    # keyvault
    ("keyvault", "Vault"): keyvault.Vault,
    ("keyvault", "Secret"): keyvault.Secret,
    # network
    ("network", "VirtualNetwork"): network.VirtualNetwork,
    ("network", "PrivateDnsZoneGroup"): network.PrivateDnsZoneGroup,
    ("network", "Subnet"): network.Subnet,
    ("network", "VirtualWan"): network.VirtualWan,
    ("network", "VirtualHub"): network.VirtualHub,
    ("network", "VpnServerConfiguration"): network.VpnServerConfiguration,
    ("network", "P2sVpnGateway"): network.P2sVpnGateway,
    ("network", "HubVirtualNetworkConnection"): network.HubVirtualNetworkConnection,
    ("network", "Zone"): None,  # dns.Zone -> namespace mismatch (dns != network)
    ("network", "RecordSet"): None,  # dns.RecordSet -> namespace mismatch
    ("network", "PrivateRecordSet"): None,  # privatedns.PrivateRecordSet -> namespace mismatch
    ("network", "PrivateEndpoint"): network.PrivateEndpoint,
    # operationalinsights
    ("operationalinsights", "Workspace"): operationalinsights.Workspace,
    # providerhub
    ("providerhub", "ProviderRegistration"): providerhub.ProviderRegistration,
    ("providerhub", "ResourceTypeRegistration"): providerhub.ResourceTypeRegistration,
    # resources
    ("resources", "ResourceGroup"): resources.ResourceGroup,
    # servicebus
    ("servicebus", "Namespace"): servicebus.Namespace,
    # sql
    ("sql", "Database"): sql.Database,
    ("sql", "Server"): sql.Server,
    # search
    ("search", "Service"): search.Service,
    # storage
    ("storage", "StorageAccount"): storage.StorageAccount,
    ("storage", "Table"): storage.Table,
    ("storage", "Queue"): storage.Queue,
    ("storage", "BlobContainer"): storage.BlobContainer,
    ("storage", "FileShare"): storage.FileShare,
    # web
    ("web", "AppServicePlan"): web.AppServicePlan,
    ("web", "WebApp"): web.WebApp,
}

# Expected autoname output for v2 resources (using stack fixture: workload="workload", env="test",
# location="northeurope").
V2_NAMING_EXPECTED: dict[tuple[str, str], str] = {
    ("app", "ContainerApp"): "app-workload-test-neu-01",
    ("app", "Certificate"): "caecert--workload-test-neu-01",
    ("app", "ManagedEnvironment"): "cae-workload-test-neu-01",
    ("appconfiguration", "ConfigurationStore"): "appcs-workload-test-neu-01",
    ("appconfiguration", "KeyValue"): "appcsk-workload-test-neu-01",
    ("authorization", "RoleAssignment"): "iam-workload-test-neu-01",
    ("cognitiveservices", "Account"): "oai-workload-test-neu-01",
    ("containerregistry", "Registry"): "CrWorkloadTestNeu01",
    ("eventgrid", "Domain"): "evgd-workload-test-neu-01",
    ("eventgrid", "DomainTopic"): "evgt-workload-test-neu-01",
    ("eventhub", "Namespace"): "evhns-workload-test-neu-01",
    ("eventhub", "NamespaceAuthorizationRule"): "evhns-key-workload-test-neu-01",
    ("keyvault", "Vault"): "KvWorkloadTestNeu01",
    ("keyvault", "Secret"): "kvs-workload-test-neu-01",
    ("network", "VirtualNetwork"): "vnet-workload-test-neu-01",
    ("network", "PrivateDnsZoneGroup"): "pdzg-workload-test-neu-01",
    ("network", "Subnet"): "snet-workload-test-neu-01",
    ("network", "VirtualWan"): "vwan-workload-test-neu-01",
    ("network", "VirtualHub"): "vhub-workload-test-neu-01",
    ("network", "VpnServerConfiguration"): "vpnconf-workload-test-neu-01",
    ("network", "P2sVpnGateway"): "vpng-workload-test-neu-01",
    ("network", "HubVirtualNetworkConnection"): "vhubc-workload-test-neu-01",
    ("network", "PrivateEndpoint"): "pep-workload-test-neu-01",
    ("operationalinsights", "Workspace"): "log-workload-test-neu-01",
    ("providerhub", "ProviderRegistration"): "proreg-workload-test-neu-01",
    ("providerhub", "ResourceTypeRegistration"): "prov-workload-test-neu-01",
    ("resources", "ResourceGroup"): "rg-workload-test-neu-01",
    ("servicebus", "Namespace"): "sbns-workload-test-neu-01",
    ("sql", "Database"): "sqldb-workload-test-neu-01",
    ("sql", "Server"): "sql-workload-test-neu-01",
    ("search", "Service"): "srch-workload-test-neu-01",
    ("storage", "StorageAccount"): "stworkloadtestneu01",
    ("storage", "Table"): "sttbl-workload-test-neu-01",
    ("storage", "Queue"): "stq-workload-test-neu-01",
    ("storage", "BlobContainer"): "stctr-workload-test-neu-01",
    ("storage", "FileShare"): "stfs-workload-test-neu-01",
    ("web", "AppServicePlan"): "asp-workload-test-neu-01",
    ("web", "WebApp"): "app-workload-test-neu-01",
}

# Resources that cannot be tested via v2 autoname, with documented reasons.
V2_UNTESTABLE_RESOURCES: dict[tuple[str, str], str] = {
    ("eventhub", "Eventhub"): (
        "Class name mismatch: Pulumi class is 'EventHub' but v2 metadata key is 'Eventhub'. "
        "resource_meta(eventhub.EventHub) raises KeyError."
    ),
    ("insights", "Component"): (
        "Namespace mismatch: Pulumi module is 'applicationinsights' but v2 metadata key is 'insights'. "
        "resource_meta(applicationinsights.Component) raises KeyError."
    ),
    ("insights", "Diagnosticsetting"): (
        "Namespace mismatch: Pulumi module is 'monitor' but v2 metadata key is 'insights'. "
        "resource_meta(monitor.DiagnosticSetting) raises KeyError."
    ),
    ("network", "Zone"): (
        "Namespace mismatch: Pulumi module is 'dns' but v2 metadata key is 'network'. "
        "resource_meta(dns.Zone) would look in 'dns' namespace which does not exist in v2."
    ),
    ("network", "RecordSet"): (
        "Namespace mismatch: Pulumi module is 'dns' but v2 metadata key is 'network'. "
        "Also has trailing comma in prefix: 'dnsr,' (likely typo)."
    ),
    ("network", "PrivateRecordSet"): (
        "Namespace mismatch: Pulumi module is 'privatedns' but v2 metadata key is 'network'."
    ),
}


def _v2_testable_params() -> list[tuple[str, str]]:
    """Return (ns_key, class_name) pairs that can be tested with resource_meta().autoname()."""
    params = []
    for (ns_key, class_name), cls in _V2_PULUMI_CLASSES.items():
        if cls is not None:
            params.append((ns_key, class_name))
    return params


@pytest.mark.parametrize(
    ("ns_key", "class_name"),
    _v2_testable_params(),
    ids=lambda p: p if isinstance(p, str) else "",
)
def test_v2_naming_end_to_end(stack: AzureStack, ns_key: str, class_name: str) -> None:
    """resource_meta(PulumiClass).autoname(stack) must produce the exact expected name."""
    pulumi_class = _V2_PULUMI_CLASSES[(ns_key, class_name)]
    assert pulumi_class is not None

    meta = resource_meta(pulumi_class)
    result = meta.autoname(stack=stack)
    expected = V2_NAMING_EXPECTED[(ns_key, class_name)]
    assert result == expected, (
        f"V2 naming mismatch for {ns_key}.{class_name}: expected {expected!r}, got {result!r}"
    )


def test_v2_untestable_resources_documented() -> None:
    """All v2 resources that cannot be tested must have a documented reason."""
    for (ns_key, class_name), cls in _V2_PULUMI_CLASSES.items():
        if cls is None:
            assert (ns_key, class_name) in V2_UNTESTABLE_RESOURCES, (
                f"v2 resource ({ns_key}, {class_name}) has no Pulumi class mapping "
                f"but is not documented in V2_UNTESTABLE_RESOURCES"
            )


def test_v2_all_testable_resources_have_expected_names() -> None:
    """Every testable v2 resource must have an expected naming result."""
    for ns_key, class_name in _v2_testable_params():
        assert (ns_key, class_name) in V2_NAMING_EXPECTED, (
            f"Missing expected name for testable v2 resource ({ns_key}, {class_name})"
        )


# ---------------------------------------------------------------------------
# 6. Cross-system consistency test
# ---------------------------------------------------------------------------

# Mapping from v1 module_path to (v2_namespace, v2_class_name) for resources that
# exist in both systems.
V1_TO_V2_MAPPING: dict[str, tuple[str, str]] = {
    "pulumi_azure_native.resources.resource_group": ("resources", "ResourceGroup"),
    "pulumi_azure_native.operationalinsights.workspace": ("operationalinsights", "Workspace"),
    "pulumi_azure_native.containerregistry.registry": ("containerregistry", "Registry"),
    "pulumi_azure_native.keyvault.vault": ("keyvault", "Vault"),
    "pulumi_azure_native.keyvault.secret": ("keyvault", "Secret"),
    "pulumi_azure_native.storage.storage_account": ("storage", "StorageAccount"),
    "pulumi_azure_native.storage.table": ("storage", "Table"),
    "pulumi_azure_native.storage.blob_container": ("storage", "BlobContainer"),
    "pulumi_azure_native.storage.queue": ("storage", "Queue"),
    "pulumi_azure_native.storage.file_share": ("storage", "FileShare"),
    "pulumi_azure_native.storage.file_service_properties": ("storage", "FileServiceProperties"),
    "pulumi_azure_native.network.private_dns_zone_group": ("network", "PrivateDnsZoneGroup"),
    "pulumi_azure_native.network.virtual_network": ("network", "VirtualNetwork"),
    "pulumi_azure_native.network.subnet": ("network", "Subnet"),
    "pulumi_azure_native.network.virtual_wan": ("network", "VirtualWan"),
    "pulumi_azure_native.network.virtual_hub": ("network", "VirtualHub"),
    "pulumi_azure_native.network.vpn_server_configuration": ("network", "VpnServerConfiguration"),
    "pulumi_azure_native.network.p2s_vpn_gateway": ("network", "P2sVpnGateway"),
    "pulumi_azure_native.network.hub_virtual_network_connection": (
        "network",
        "HubVirtualNetworkConnection",
    ),
    "pulumi_azure_native.network.private_endpoint": ("network", "PrivateEndpoint"),
    "pulumi_azure_native.network.vpn_gateway": ("network", "VpnGateway"),
    "pulumi_azure_native.network.virtual_network_gateway": (
        "network",
        "VirtualNetworkGateway",
    ),
    "pulumi_azure_native.network.virtual_network_gateway_connection": (
        "network",
        "VirtualNetworkGatewayConnection",
    ),
    "pulumi_azure_native.network.local_network_gateway": ("network", "LocalNetworkGateway"),
    "pulumi_azure_native.network.route_table": ("network", "RouteTable"),
    "pulumi_azure_native.network.network_interface": ("network", "NetworkInterface"),
    "pulumi_azure_native.network.azure_firewall": ("network", "AzureFirewall"),
    "pulumi_azure_native.network.firewall_policy": ("network", "FirewallPolicy"),
    "pulumi_azure_native.network.dnssec_config": ("network", "DnssecConfig"),
    "pulumi_azure_native.app.managed_environment": ("app", "ManagedEnvironment"),
    "pulumi_azure_native.app.container_app": ("app", "ContainerApp"),
    "pulumi_azure_native.app.certificate": ("app", "Certificate"),
    "pulumi_azure_native.app.managed_certificate": ("app", "ManagedCertificate"),
    "pulumi_azure_native.app.app_resiliency": ("app", "AppResiliency"),
    "pulumi_azure_native.eventhub.namespace": ("eventhub", "Namespace"),
    "pulumi_azure_native.eventhub.event_hub": ("eventhub", "EventHub"),
    "pulumi_azure_native.eventhub.namespace_authorization_rule": (
        "eventhub",
        "NamespaceAuthorizationRule",
    ),
    "pulumi_azure_native.eventhub.namespace_network_rule_set": (
        "eventhub",
        "NamespaceNetworkRuleSet",
    ),
    "pulumi_azure_native.appconfiguration.configuration_store": (
        "appconfiguration",
        "ConfigurationStore",
    ),
    "pulumi_azure_native.appconfiguration.key_value": ("appconfiguration", "KeyValue"),
    "pulumi_azure_native.authorization.role_assignment": ("authorization", "RoleAssignment"),
    "pulumi_azure_native.cognitiveservices.account": ("cognitiveservices", "Account"),
    "pulumi_azure_native.eventgrid.domain": ("eventgrid", "Domain"),
    "pulumi_azure_native.eventgrid.domain_topic": ("eventgrid", "DomainTopic"),
    "pulumi_azure_native.providerhub.provider_registration": (
        "providerhub",
        "ProviderRegistration",
    ),
    "pulumi_azure_native.providerhub.resource_type_registration": (
        "providerhub",
        "ResourceTypeRegistration",
    ),
    "pulumi_azure_native.search.service": ("search", "Service"),
    "pulumi_azure_native.servicebus.namespace": ("servicebus", "Namespace"),
    "pulumi_azure_native.servicebus.queue": ("servicebus", "Queue"),
    "pulumi_azure_native.servicebus.topic": ("servicebus", "Topic"),
    "pulumi_azure_native.servicebus.namespace_network_rule_set": (
        "servicebus",
        "NamespaceNetworkRuleSet",
    ),
    "pulumi_azure_native.servicebus.namespace_ip_filter_rule": (
        "servicebus",
        "NamespaceIpFilterRule",
    ),
    "pulumi_azure_native.sql.database": ("sql", "Database"),
    "pulumi_azure_native.sql.server": ("sql", "Server"),
    "pulumi_azure_native.sql.firewall_rule": ("sql", "FirewallRule"),
    "pulumi_azure_native.sql.server_dns_alias": ("sql", "ServerDnsAlias"),
    "pulumi_azure_native.sql.elastic_pool": ("sql", "ElasticPool"),
    "pulumi_azure_native.sql.job_agent": ("sql", "JobAgent"),
    "pulumi_azure_native.sql.job_target_group": ("sql", "JobTargetGroup"),
    "pulumi_azure_native.sql.job": ("sql", "Job"),
    "pulumi_azure_native.sql.job_step": ("sql", "JobStep"),
    "pulumi_azure_native.web.app_service": ("web", "WebApp"),
    "pulumi_azure_native.web.app_service_plan": ("web", "AppServicePlan"),
}

# Known prefix discrepancies between v1 and v2.
# After Phase 2 migration, all known discrepancies have been resolved.
KNOWN_PREFIX_DISCREPANCIES: dict[str, dict[str, str]] = {}


# Mapping from v1 module_path to (v2_namespace, v2_class_name) for resources that
# exist in both systems but under DIFFERENT namespace keys.
V1_TO_V2_DIFFERENT_PATH_MAPPING: dict[str, tuple[str, str]] = {
    "pulumi_azure_native.applicationinsights.component": ("insights", "Component"),
    "pulumi_azure_native.monitor.diagnostic_setting": ("insights", "DiagnosticSetting"),
}


def _get_v2_prefix(ns_key: str, class_name: str) -> str:
    """Extract the prefix from v2 metadata, handling the AppServicePlan special case."""
    resource_data = _azure_resource_meta["pulumi_azure_native"][ns_key]["resources"][class_name]
    if "naming" in resource_data:
        return resource_data["naming"]["prefix"]
    # AppServicePlan has prefix at top level (bug)
    return resource_data["prefix"]


@pytest.mark.parametrize(
    "v1_module_path",
    sorted(V1_TO_V2_MAPPING.keys()),
    ids=lambda p: p.split(".")[-1],
)
def test_cross_system_prefix_consistency(v1_module_path: str) -> None:
    """For resources in both v1 and v2, prefixes must match (with known exceptions)."""
    v1_prefix = RESOURCE_PREFIXES[v1_module_path]["prefix"]
    ns_key, class_name = V1_TO_V2_MAPPING[v1_module_path]
    v2_prefix = _get_v2_prefix(ns_key, class_name)

    if v1_module_path in KNOWN_PREFIX_DISCREPANCIES:
        discrepancy = KNOWN_PREFIX_DISCREPANCIES[v1_module_path]
        assert v1_prefix == discrepancy["v1_prefix"], (
            f"Expected v1 prefix '{discrepancy['v1_prefix']}' but got '{v1_prefix}'"
        )
        assert v2_prefix == discrepancy["v2_prefix"], (
            f"Expected v2 prefix '{discrepancy['v2_prefix']}' but got '{v2_prefix}'"
        )
    else:
        assert v1_prefix == v2_prefix, (
            f"Prefix mismatch for {v1_module_path}: v1='{v1_prefix}', v2='{v2_prefix}' "
            f"(v2 key: {ns_key}.{class_name}). "
            f"If this is expected, add to KNOWN_PREFIX_DISCREPANCIES."
        )


@pytest.mark.parametrize(
    "v1_module_path",
    sorted(V1_TO_V2_DIFFERENT_PATH_MAPPING.keys()),
    ids=lambda p: p.split(".")[-1],
)
def test_cross_system_prefix_consistency_different_paths(v1_module_path: str) -> None:
    """For resources in both v1 and v2 under different namespace keys, prefixes must match."""
    v1_prefix = RESOURCE_PREFIXES[v1_module_path]["prefix"]
    ns_key, class_name = V1_TO_V2_DIFFERENT_PATH_MAPPING[v1_module_path]
    v2_prefix = _get_v2_prefix(ns_key, class_name)

    if v1_module_path in KNOWN_PREFIX_DISCREPANCIES:
        discrepancy = KNOWN_PREFIX_DISCREPANCIES[v1_module_path]
        assert v1_prefix == discrepancy["v1_prefix"], (
            f"Expected v1 prefix '{discrepancy['v1_prefix']}' but got '{v1_prefix}'"
        )
        assert v2_prefix == discrepancy["v2_prefix"], (
            f"Expected v2 prefix '{discrepancy['v2_prefix']}' but got '{v2_prefix}'"
        )
    else:
        assert v1_prefix == v2_prefix, (
            f"Prefix mismatch for {v1_module_path}: v1='{v1_prefix}', v2='{v2_prefix}' "
            f"(v2 key: {ns_key}.{class_name}). "
            f"If this is expected, add to KNOWN_PREFIX_DISCREPANCIES."
        )


def test_cross_system_v1_only_resources() -> None:
    """Document resources that exist only in v1 (RESOURCE_PREFIXES) but not v2."""
    v1_only: set[str] = set(RESOURCE_PREFIXES.keys()) - set(V1_TO_V2_MAPPING.keys())
    # These are the resources only in v1. We assert the exact set so any addition/removal
    # is caught.
    expected_v1_only = {
        "pulumi_azure_native.monitor.diagnostic_setting",
        "pulumi_azure_native.applicationinsights.component",
        "pulumi_azure_native.dns.zone",
        "pulumi_azure_native.dns.record_set",
        "pulumi_azure_native.privatedns.private_record_set",
        "pulumi_azure_native.dnsresolver.dns_resolver",
        "pulumi_azure_native.dnsresolver.inbound_endpoint",
        "pulumi_azure_native.dnsresolver.outbound_endpoint",
        "pulumi_azure_native.dnsresolver.dns_forwarding_ruleset",
        "pulumi_azure_native.managedidentity.user_assigned_identity",
        "pulumi_azure_native.dbforpostgresql.server",
        "pulumi_azure_native.dbforpostgresql.administrator",
        "pulumi_azure_native.dbforpostgresql.configuration",
        "pulumi_random.random_password",
        "pulumi_azure_native.compute.virtual_machine",
        "pulumi_azure_native.compute.disk",
        "pulumi_azure_native.recoveryservices.vault",
        "pulumi_azure_native.recoveryservices.protection_policy",
    }
    assert v1_only == expected_v1_only, (
        f"V1-only resources changed.\n"
        f"  Newly v1-only: {v1_only - expected_v1_only}\n"
        f"  No longer v1-only: {expected_v1_only - v1_only}"
    )


def test_cross_system_v2_only_resources() -> None:
    """Document resources that exist only in v2 (_azure_resource_meta) but not v1."""
    v2_resources: set[tuple[str, str]] = set()
    for ns_key, ns_data in _azure_resource_meta["pulumi_azure_native"].items():
        for class_name in ns_data["resources"]:
            v2_resources.add((ns_key, class_name))

    v1_mapped_v2: set[tuple[str, str]] = set(V1_TO_V2_MAPPING.values())
    v2_only = v2_resources - v1_mapped_v2

    # After Phase 2 migration, some v2 entries are aliases (different casing/naming)
    # that have v1 counterparts under a different path mapping.
    v2_with_v1_counterpart_different_path: dict[tuple[str, str], str] = {
        # v2 "insights.Component" corresponds to v1 "applicationinsights.component"
        ("insights", "Component"): "pulumi_azure_native.applicationinsights.component",
        # v2 "insights.Diagnosticsetting" corresponds to v1 "monitor.diagnostic_setting"
        ("insights", "Diagnosticsetting"): "pulumi_azure_native.monitor.diagnostic_setting",
        # v2 "insights.DiagnosticSetting" is an alias alongside "Diagnosticsetting"
        ("insights", "DiagnosticSetting"): "pulumi_azure_native.monitor.diagnostic_setting",
        # v2 "eventhub.Eventhub" is an alias for "EventHub" (different casing)
        ("eventhub", "Eventhub"): "pulumi_azure_native.eventhub.event_hub",
    }

    expected_v2_only = set(v2_with_v1_counterpart_different_path.keys())
    assert v2_only == expected_v2_only, (
        f"V2-only resources changed.\n"
        f"  Newly v2-only: {v2_only - expected_v2_only}\n"
        f"  No longer v2-only: {expected_v2_only - v2_only}"
    )


def test_cross_system_blob_container_prefix_unified() -> None:
    """Verify the BlobContainer prefix is unified after Phase 2 migration."""
    v1_prefix = RESOURCE_PREFIXES["pulumi_azure_native.storage.blob_container"]["prefix"]
    v2_prefix = _azure_resource_meta["pulumi_azure_native"]["storage"]["resources"][
        "BlobContainer"
    ]["naming"]["prefix"]
    # After Phase 2 migration, both use "stctr" (the v1/production value)
    assert v1_prefix == "stctr"
    assert v2_prefix == "stctr"
    assert v1_prefix == v2_prefix


# ---------------------------------------------------------------------------
# 7. API contract tests
# ---------------------------------------------------------------------------


class TestGetPrefixContract:
    """Tests for the get_prefix() function contract."""

    def test_returns_dict(self) -> None:
        mock = _MockPulumiClass("pulumi_azure_native.resources.resource_group")
        result = get_prefix(mock)
        assert isinstance(result, dict)

    def test_result_has_prefix_key(self) -> None:
        mock = _MockPulumiClass("pulumi_azure_native.resources.resource_group")
        result = get_prefix(mock)
        assert "prefix" in result
        assert isinstance(result["prefix"], str)

    def test_raises_value_error_on_unknown_resource(self) -> None:
        mock = _MockPulumiClass("pulumi_azure_native.nonexistent.resource")
        with pytest.raises(ValueError, match="Resource type has not been defined"):
            get_prefix(mock)

    def test_signature(self) -> None:
        sig = inspect.signature(get_prefix)
        params = list(sig.parameters.keys())
        assert params == ["resource_type"]
        assert sig.return_annotation == dict[str, Any]

    def test_normalizes_version_suffix(self) -> None:
        """Versioned module paths should be normalized to the base path."""
        mock = _MockPulumiClass("pulumi_azure_native.resources.v20231101.resource_group")
        result = get_prefix(mock)
        assert result["prefix"] == "rg"


class TestResourceNamerContract:
    """Tests for the resource_namer() function contract."""

    def test_returns_string(self) -> None:
        mock = _MockPulumiClass("pulumi_azure_native.resources.resource_group")
        result = resource_namer(mock, "wl", "dev", "westeurope", "01")
        assert isinstance(result, str)

    def test_raises_value_error_on_unknown_resource(self) -> None:
        mock = _MockPulumiClass("pulumi_azure_native.nonexistent.resource")
        with pytest.raises(ValueError, match="Resource type has not been defined"):
            resource_namer(mock, "wl", "dev", "westeurope", "01")

    def test_raises_value_error_on_unknown_region(self) -> None:
        mock = _MockPulumiClass("pulumi_azure_native.resources.resource_group")
        with pytest.raises(ValueError, match="Region settings have not been defined"):
            resource_namer(mock, "wl", "dev", "invalid_region", "01")

    def test_signature(self) -> None:
        sig = inspect.signature(resource_namer)
        params = list(sig.parameters.keys())
        assert params == [
            "resource_type",
            "workload_name",
            "env",
            "location",
            "instance_number",
        ]
        assert sig.return_annotation is str


class TestLocationAbbrContract:
    """Tests for the location_abbr() function contract."""

    def test_returns_string(self) -> None:
        result = location_abbr("westeurope")
        assert isinstance(result, str)

    def test_raises_value_error_on_unknown_region(self) -> None:
        with pytest.raises(ValueError, match="Region settings have not been defined"):
            location_abbr("unknownregion")

    def test_signature(self) -> None:
        sig = inspect.signature(location_abbr)
        params = list(sig.parameters.keys())
        assert params == ["location"]
        assert sig.return_annotation is str


class TestResourceMetaContract:
    """Tests for the resource_meta() function contract."""

    def test_returns_azure_resource_metadata(self) -> None:
        result = resource_meta(resources.ResourceGroup)
        assert isinstance(result, AzureResourceMetadata)

    def test_result_has_naming_rule(self) -> None:
        result = resource_meta(resources.ResourceGroup)
        assert isinstance(result.naming, ResourceNameRule)

    def test_raises_on_unknown_resource(self) -> None:
        """resource_meta raises an error for unknown resource classes."""
        # The current implementation raises KeyError (from dict lookup), not ValueError.
        # This documents the actual behavior.
        with pytest.raises((KeyError, IndexError)):
            resource_meta(object)

    def test_autoname_returns_string(self, stack: AzureStack) -> None:
        result = resource_meta(resources.ResourceGroup).autoname(stack=stack)
        assert isinstance(result, str)

    def test_autoname_signature(self) -> None:
        sig = inspect.signature(AzureResourceMetadata.autoname)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "stack" in params
        assert "workload_name" in params
        assert "separator" in params
        assert "instance_number" in params
        assert sig.return_annotation is str

    def test_signature(self) -> None:
        sig = inspect.signature(resource_meta)
        params = list(sig.parameters.keys())
        assert params == ["obj"]
        assert sig.return_annotation == AzureResourceMetadata


class TestResourceNameRuleModel:
    """Tests for the ResourceNameRule Pydantic model contract."""

    def test_defaults(self) -> None:
        rule = ResourceNameRule(prefix="test")
        assert rule.prefix == "test"
        assert rule.alphanumeric is False
        assert rule.lowercase is False
        assert rule.max_length is None

    def test_all_fields(self) -> None:
        rule = ResourceNameRule(
            prefix="kv",
            alphanumeric=True,
            lowercase=True,
            max_length=24,
        )
        assert rule.prefix == "kv"
        assert rule.alphanumeric is True
        assert rule.lowercase is True
        assert rule.max_length == 24

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            ResourceNameRule(prefix="test", unknown_field="bad")  # type: ignore[call-arg]

from typing import Any, Dict

LOCATION_ABBR: Dict[str, str] = {
    "westeurope": "weu",
    "northeurope": "neu",
    "norwayeast": "noe",
    "norwaywest": "now",
    "swedencentral": "sec",
}

RESOURCE_PREFIXES: Dict[str, Any] = {
    "pulumi_azure_native.resources.resource_group": {"prefix": "rg"},
    "pulumi_azure_native.operationalinsights.workspace": {
        "prefix": "log",
    },
    "pulumi_azure_native.containerregistry.registry": {
        "prefix": "cr",
        "alphanumeric": True,
    },
    "pulumi_azure_native.insights.diagnosticsetting": {
        "prefix": "diag",
    },
    "pulumi_azure_native.web.app_service_plan": {
        "prefix": "asp",
    },
    "pulumi_azure_native.web.app_service": {
        "prefix": "app",
    },
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
    "pulumi_azure_native.network.private_dns_zone_group": {
        "prefix": "pdzg",
    },
    "pulumi_azure_native.app.managed_environment": {
        "prefix": "cae",
        "max_length": 60,
    },
    "pulumi_azure_native.network.virtual_network": {
        "prefix": "vnet",
    },
    "pulumi_azure_native.network.subnet": {
        "prefix": "snet",
    },
    "pulumi_azure_native.network.virtual_wan": {
        "prefix": "vwan",
    },
    "pulumi_azure_native.network.virtual_hub": {
        "prefix": "vhub",
    },
    "pulumi_azure_native.network.vpn_server_configuration": {
        "prefix": "vpnconf",
    },
    "pulumi_azure_native.network.p2s_vpn_gateway": {
        "prefix": "vpng",
    },
    "pulumi_azure_native.network.hub_virtual_network_connection": {
        "prefix": "vhubc",
    },
    "pulumi_azure_native.eventhub.namespace": {"prefix": "evhns"},
    "pulumi_azure_native.eventhub.event_hub": {"prefix": "evh"},
    "pulumi_azure_native.storage.table": {"prefix": "sttbl"},
    "pulumi_azure_native.storage.queue": {"prefix": "stq"},
    "pulumi_azure_native.providerhub.provider_registration": {"prefix": "proreg"},
    "pulumi_azure_native.providerhub.resource_type_registration": {"prefix": "prov"},
    "pulumi_azure_native.eventhub.namespace_authorization_rule": {"prefix": "evhns-key"},
    "pulumi_azure_native.keyvault.secret": {"prefix": "kvs"},
    "pulumi_azure_native.app.container_app": {"prefix": "app"},
    "pulumi_azure_native.app.certificate": {"prefix": "caecert-"},
    "pulumi_azure_native.insights.component": {"prefix": "appi"},
    "pulumi_azure_native.network.zone": {"prefix": "dns"},
    "pulumi_azure_native.network.record_set": {"prefix": "dnsr"},
    "pulumi_azure_native.network.private_record_set": {"prefix": "dnsr"},
    "pulumi_azure_native.network.vpn_gateway": {"prefix": "vpng"},
    "pulumi_azure_native.network.dns_resolver": {"prefix": "dnspr"},
    "pulumi_azure_native.network.inbound_endpoint": {"prefix": "in"},
    "pulumi_azure_native.network.outbound_endpoint": {"prefix": "out"},
    "pulumi_azure_native.network.dns_forwarding_ruleset": {"prefix": "dnsfrs"},
    "pulumi_azure_native.authorization.role_assignment": {"prefix": "iam"},
    "pulumi_azure_native.appconfiguration.configuration_store": {"prefix": "appcs"},
    "pulumi_azure_native.appconfiguration.key_value": {"prefix": "appcsk"},
    "pulumi_azure_native.eventgrid.domain": {"prefix": "evgd"},
    "pulumi_azure_native.eventgrid.domain_topic": {"prefix": "evgt"},
    "pulumi_azure_native.network.private_endpoint": {"prefix": "pep"},
    "pulumi_azure_native.search.service": {"prefix": "srch"},
    # See Cloud Adoption Framework Abbreviations:
    # https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/azure-best-practices/resource-abbreviations
}

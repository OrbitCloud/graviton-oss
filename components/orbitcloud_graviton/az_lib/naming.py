""" Helper functions for creating Azure related resources """

import re
from typing import Any, Dict

RESOURCE_NAMING: Dict[str, Any] = {
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
}

LOCATION_ABBR: Dict[str, str] = {
    "westeurope": "weu",
    "northeurope": "neu",
    "norwayeast": "noe",
    "norwaywest": "now",
    "swedencentral": "sec",
}


def resource_opts(resource_type) -> Dict[str, Any]:
    """Return a resource prefix for a given resource type"""
    # Extract the base module path without the version
    base_module_path = re.sub(r"\.v\d{8}", "", resource_type.__module__)

    # Try to get the options using the base module path
    opts: Any | None = RESOURCE_NAMING.get(base_module_path)

    if not opts:
        raise ValueError(f"Resource type has not been defined: {resource_type}")

    return opts


def resource_namer(resource_type, workload_name: str, env, location, instance_number: str = "01") -> str:
    """Return a resource name for a given resource type"""
    opts: Dict[str, Any] = resource_opts(resource_type=resource_type)
    prefix: str | Any = opts.get("prefix")
    location_short: str = location_abbr(location=location)
    separator: str = "-"

    if opts.get("alphanumeric"):
        separator = ""
        workload_name = (
            "".join([word.title() for word in workload_name.split("-")])
            if "-" in workload_name
            else workload_name.title()
        )

    name_elements = [
        prefix,
        workload_name,
        env,
        location_short,
        instance_number,
    ]

    resource_name = separator.join([element.title() if separator == "" else element for element in name_elements])

    return resource_name.lower() if opts.get("lowercase") else resource_name


def location_abbr(location) -> str:
    """Return a location abbreviation for a given location"""
    abbr = LOCATION_ABBR.get(location)
    if not abbr:
        raise ValueError(f"Abbreviation has not been defined for: {location}")
    return abbr

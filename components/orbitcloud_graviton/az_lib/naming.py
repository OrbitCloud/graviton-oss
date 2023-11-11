""" Helper functions for creating Azure related resources """

from typing import Any, Dict
import re

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
    },
    "pulumi_azure_native.storage.storage_account": {
        "prefix": "st",
        "alphanumeric": True,
        "lowercase": True,
    },
    "pulumi_azure_native.network.private_dns_zone_group": {
        "prefix": "pdzg",
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


def resource_namer(
    resource_type, workload_name, env, location, instance_number: str = "01"
) -> str:
    """Return a resource name for a given resource type"""
    opts: Dict[str, Any] = resource_opts(resource_type=resource_type)
    prefix: str | Any = opts.get("prefix")
    location_short: str = location_abbr(location=location)

    if opts.get("alphanumeric") and opts.get("lowercase"):
        return (
            f"{prefix.lower()}{workload_name.lower()}"
            f"{env.lower()}{location_short.lower()}{instance_number}"
        )
    elif opts.get("alphanumeric"):
        return (
            f"{prefix.capitalize()}{workload_name.capitalize()}"
            f"{env.capitalize()}{location_short.capitalize()}{instance_number}"
        )

    return f"{prefix}-{workload_name}-{env}-{location_short}-{instance_number}"


def location_abbr(location) -> str:
    """Return a location abbreviation for a given location"""
    abbr = LOCATION_ABBR.get(location)
    if not abbr:
        raise ValueError(f"Abbreviation has not been defined for: {location}")
    return abbr

""" Helper functions for creating Azure related resources """

RESOURCE_PREFIXES = {
    "pulumi_azure_native.resources.resource_group": "rg",
    "pulumi_azure_native.operationalinsights.workspace": "log",
}

LOCATION_ABBR = {
    "westeurope": "weu",
    "northeurope": "neu",
    "norwayeast": "noe",
    "norwaywest": "now",
    "swedencentral": "sec",
}


def resource_namer(
    resource_type, workload_name, env, location, instance_number: str = "01"
) -> str:
    """Return a resource name for a given resource type"""
    prefix = resource_prefix(resource_type)
    location_short = location_abbr(location)
    return f"{prefix}-{workload_name}-{env}-{location_short}-{instance_number}"


def location_abbr(location: str) -> str:
    """Return a location abbreviation for a given location"""
    abbr = LOCATION_ABBR.get(location)
    if not abbr:
        raise ValueError(f"Abbreviation has not been defined for: {location}")
    return abbr


def resource_prefix(resource_type) -> str:
    """Return a resource prefix for a given resource type"""
    prefix = RESOURCE_PREFIXES.get(resource_type.__module__)
    if not prefix:
        raise ValueError(f"Prefix has not been defined for: {resource_type.__module__}")
    return prefix

"""Helper functions for creating Azure related resources"""

import re
from typing import Any

from .helpers import location_abbr
from .metadata.loader import RESOURCE_PREFIXES


def get_prefix(resource_type) -> dict[str, Any]:
    """Return a resource prefix for a given resource type"""

    # pulumi_azure_native_app_v20241002preview.app.container_app.ContainerApp -> pulumi_azure_native.app.container_app.ContainerApp
    # pulumi_azure_native.app.container_app.ContainerApp
    # pulumi_kubernetes_v1.apps.v1.Deployment -> pulumi_kubernetes.apps.v1.Deployment
    module_path = resource_type.__module__

    if module_path.startswith("pulumi_azure_native_"):
        # Convert pulumi_azure_native_<name> to pulumi_azure_native.<name>
        module_path = re.sub(r"^pulumi_azure_native_([^\.]+)", r"pulumi_azure_native", module_path)

    # Remove version suffixes: _vYYYYMMDD[preview] and .vYYYYMMDD
    module_path = re.sub(r"(_v\d{8}(preview)?)|(\.v\d{8})", "", module_path)

    # Try to get the options using the normalized module path
    opts: Any | None = RESOURCE_PREFIXES.get(module_path)

    if not opts:
        raise ValueError(f"Resource type has not been defined: {resource_type}")

    return opts


def resource_namer(
    resource_type, workload_name: str, env, location, instance_number: str = "01"
) -> str:
    """Return a resource name for a given resource type"""
    opts: dict[str, Any] = get_prefix(resource_type=resource_type)
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

    name_elements: list[str] = [
        prefix,
        workload_name,
        env,
        location_short,
        instance_number,
    ]

    resource_name = separator.join(
        [element.title() if separator == "" else element for element in name_elements]
    )

    return resource_name.lower() if opts.get("lowercase") else resource_name

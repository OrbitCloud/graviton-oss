"""Azure ResourceGroup Component"""

from typing import Optional, Mapping

import pulumi
from pulumi_azure_native import resources

from orbitcloud_graviton.azure_helpers.core import resource_namer


def resource_group(
    workload_name: str,
    location: str,
    env: str = "dev",
    tags: Optional[Mapping[str, str]] = None,
    opts: Optional[pulumi.ResourceOptions] = None,
) -> resources.ResourceGroup:
    """Create an Azure ResourceGroup"""

    resource_name = resource_namer(
        resources.ResourceGroup, workload_name, env, location
    )

    if tags is None:
        tags = {"env": env}
    elif tags is not None and tags.get("env") is None:
        tags.update({"env": env})

    return resources.ResourceGroup(
        resource_name,
        location=location,
        tags=tags,
        opts=opts,
    )

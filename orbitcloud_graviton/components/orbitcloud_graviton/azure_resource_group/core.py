"""Azure ResourceGroup Component"""

from typing import Optional, Dict

import pulumi
from pulumi_azure_native import resources

from orbitcloud_graviton.azure_helpers import resource_namer


def resource_group(
    workload_name: str,
    location: str,
    env: str,
    tags: Optional[Dict[str, str]] = None,
    opts: Optional[pulumi.ResourceOptions] = None,
) -> resources.ResourceGroup:
    """Create an Azure ResourceGroup"""

    resource_name = resource_namer(
        resource_type=resources.ResourceGroup,
        workload_name=workload_name,
        env=env,
        location=location,
    )

    if tags is None:
        tags = {}
    tags.setdefault("env", env)

    return resources.ResourceGroup(
        resource_name,
        location=location,
        tags=tags,
        opts=opts,
    )

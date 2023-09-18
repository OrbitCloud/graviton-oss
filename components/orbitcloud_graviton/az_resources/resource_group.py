"""Azure ResourceGroup Component"""

from typing import Dict, Optional

import pulumi
from orbitcloud_graviton.az_lib import StackConfig, resource_namer
from pulumi_azure_native import resources


def az_resource_group(
    workload_name: str,
    env: str,
    location: str,
    tags: Optional[Dict[str, str]] = None,
    opts: Optional[pulumi.ResourceOptions] = None,
) -> resources.ResourceGroup:
    """Create an Azure ResourceGroup"""

    resource_name: str = resource_namer(
        resource_type=resources.ResourceGroup,
        workload_name=workload_name,
        env=env,
        location=location,
    )

    return resources.ResourceGroup(
        resource_name,
        location=location,
        tags=tags,
        opts=opts,
    )


def az_resource_group_from_config(
    config: StackConfig,
) -> resources.ResourceGroup | resources.AwaitableGetResourceGroupResult:
    """Create or get an Azure ResourceGroup from a ConfigProtocol"""

    if config.resource_group_name:
        return resources.get_resource_group(
            resource_group_name=config.resource_group_name
        )

    return az_resource_group(
        workload_name=config.workload_name,
        env=config.env,
        location=config.location,
        tags=config.tags,
    )

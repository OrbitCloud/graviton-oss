"""Azure ResourceGroup Component"""

from typing import Dict, Optional

import pulumi
from orbitcloud_graviton.az_lib import resource_namer
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

"""Azure ResourceGroup Component"""

from typing import Optional

import pulumi
from pulumi_azure_native import resources


def resource_group(
    stack,
    opts: Optional[pulumi.ResourceOptions] = None,
) -> resources.ResourceGroup:
    if stack.resource_group_name:
        existing_rg: resources.AwaitableGetResourceGroupResult = resources.get_resource_group(
            resource_group_name=stack.resource_group_name,
        )

        return resources.ResourceGroup.get(
            id=existing_rg.id,
            resource_name=existing_rg.name,
        )

    return resources.ResourceGroup(
        resource_name=stack.name_for(resources.ResourceGroup),
        location=stack.location,
        tags=stack.tags,
        opts=opts,
    )

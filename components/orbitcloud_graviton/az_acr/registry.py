from typing import List, Optional

import pulumi
from pulumi_azure_native import containerregistry
from pydantic import BaseModel, Field

from orbitcloud_graviton.pulumi_lib import AzureBase


class ContainerRegistryConfig(BaseModel):
    public_network_access: containerregistry.PublicNetworkAccess = (
        containerregistry.PublicNetworkAccess.DISABLED
    )
    ip_allow_list: Optional[List[str]] = Field(..., default_factory=list)
    admin_user_enabled: Optional[bool] = False


def container_registry(
    stack: AzureBase,
    config: ContainerRegistryConfig,
    opts: Optional[pulumi.ResourceOptions] = None,
) -> containerregistry.Registry:
    """Create container registry"""

    return containerregistry.Registry(
        resource_name=stack.name_for(containerregistry.Registry),
        admin_user_enabled=config.admin_user_enabled,
        location=stack.location,
        resource_group_name=stack.resource_group.name,
        network_rule_set=containerregistry.NetworkRuleSetArgs(
            default_action="Deny",
            # For all ip_allow_list, add ip address to network rules
            ip_rules=[
                containerregistry.IPRuleArgs(
                    action="Allow",
                    i_p_address_or_range=ip,
                )
                for ip in config.ip_allow_list
            ],
        )
        if config.ip_allow_list
        else None,
        sku=containerregistry.SkuArgs(
            name="Premium",
        ),
        opts=opts,
    )

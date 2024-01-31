from typing import Dict, List, Optional

import pulumi
from pulumi_azure_native import containerregistry, resources
from pydantic import BaseModel, Field

from orbitcloud_graviton.az_lib import resource_namer


class ContainerRegistryConfig(BaseModel):
    public_network_access: containerregistry.PublicNetworkAccess = containerregistry.PublicNetworkAccess.DISABLED
    ip_allow_list: Optional[List[str]] = Field(..., default_factory=list)
    admin_user_enabled: Optional[bool] = False


def az_containerregistry(
    resource_group: resources.ResourceGroup,
    workload_name: str,
    env: str,
    location: str,
    tags: Optional[Dict[str, str]] = None,
    ip_allow_list: Optional[list[str]] = None,
    public_network_access: Optional[str] = None,
    opts: Optional[pulumi.ResourceOptions] = None,
) -> containerregistry.Registry:
    """Create container registry"""
    if not ip_allow_list:
        ip_allow_list = []

    registry_name: str = resource_namer(
        resource_type=containerregistry.Registry,
        workload_name=workload_name,
        env=env,
        location=location,
    )

    return containerregistry.Registry(
        resource_name=registry_name,
        admin_user_enabled=False,
        location=resource_group.location,
        resource_group_name=resource_group.name,
        tags=tags,
        public_network_access=public_network_access or containerregistry.PublicNetworkAccess.DISABLED,
        network_rule_set=containerregistry.NetworkRuleSetArgs(
            default_action="Deny",
            # For all ip_allow_list, add ip address to network rules
            ip_rules=[
                containerregistry.IPRuleArgs(
                    action="Allow",
                    i_p_address_or_range=ip,
                )
                for ip in ip_allow_list
            ],
        ),
        sku=containerregistry.SkuArgs(
            name="Premium",
        ),
        opts=opts,
    )

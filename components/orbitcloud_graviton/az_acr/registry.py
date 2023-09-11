from typing import Dict, Optional
from pulumi_azure_native import resources, containerregistry
from orbitcloud_graviton.az_lib import resource_namer


def az_containerregistry(
    resource_group: resources.ResourceGroup,
    workload_name: str,
    env: str,
    location: str,
    tags: Optional[Dict[str, str]] = None,
    ip_allow_list: Optional[list[str]] = None,
    public_network_access: Optional[str] = None,
) -> containerregistry.Registry:
    """Create container registry"""

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
        public_network_access=public_network_access
        or containerregistry.PublicNetworkAccess.DISABLED,
        network_rule_set=containerregistry.NetworkRuleSetArgs(
            default_action="Deny",
            # For all ip_allow_list, add ip address to network rules
            ip_rules=list(
                map(
                    lambda ip: containerregistry.IPRuleArgs(
                        action="Allow",
                        i_p_address_or_range=ip,
                    ),
                    ip_allow_list,
                )
            )
            if ip_allow_list is not None
            else [],
        ),
        sku=containerregistry.SkuArgs(
            name="Premium",
        ),
    )

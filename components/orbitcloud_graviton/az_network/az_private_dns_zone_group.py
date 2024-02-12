from typing import Any

from pulumi_azure_native import resources

# PrivateDNSZoneGroup & PrivateZone are from different API versions so we need to import them separately for now
from pulumi_azure_native.network import v20230901 as network
from pulumi_azure_native.network.v20200601 import (
    AwaitableGetPrivateZoneResult,
    PrivateZone,
)

# Private DNS Zone Groups are used to associate a private endpoint with a private DNS zone


def az_privatednszonegroup(
    resource: Any,
    resource_group: resources.ResourceGroup | resources.AwaitableGetResourceGroupResult,
    target_resource_type: str,
    private_dns_zone: PrivateZone | AwaitableGetPrivateZoneResult | str,
) -> network.PrivateDnsZoneGroup:
    if not hasattr(resource, "name"):
        raise ValueError("target resource must have a name attribute")

        # Determine if Private DNS Zone is an object or a string (resource ID)
    if isinstance(
        private_dns_zone,
        (PrivateZone, AwaitableGetPrivateZoneResult),
    ):
        private_dns_zone_id = private_dns_zone.id
    elif isinstance(private_dns_zone, str):
        private_dns_zone_id = private_dns_zone
    else:
        raise TypeError(
            "private_dns_zone must be either a network.PrivateZone object or a Private DNS Zone Resource ID string"
        )

    private_dns_zone_group_name: str = "pdzg-" + target_resource_type

    return network.PrivateDnsZoneGroup(
        resource_name=private_dns_zone_group_name,
        name=private_dns_zone_group_name,
        private_dns_zone_configs=[
            network.PrivateDnsZoneConfigArgs(
                private_dns_zone_id=private_dns_zone_id,
                name=private_dns_zone_group_name,
            )
        ],
        resource_group_name=resource_group.name,
        private_dns_zone_group_name=private_dns_zone_group_name,
        private_endpoint_name=resource.name,
    )

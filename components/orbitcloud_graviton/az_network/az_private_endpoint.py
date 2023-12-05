from typing import Any, Dict, Optional

from dataclasses import dataclass

from pulumi_azure_native.network import v20230201 as network
from pulumi_azure_native import resources

from .az_private_dns_zone_group import az_privatednszonegroup


# TODO: Decide on how to accept subnet, only network.Subnet object or subnet id string or both. Current implementation accepts both. Stack reference?
# TODO: Consider verifying if target_resource_type is valid


@dataclass
class PrivateEndpointConfig:
    target_resource_type: str
    subnet: network.Subnet | network.AwaitableGetSubnetResult | str
    private_dns_zone_id: Optional[str] = None


def az_private_endpoint(
    resource: Any,
    resource_group: resources.ResourceGroup | resources.AwaitableGetResourceGroupResult,
    private_endpoint_config: PrivateEndpointConfig,
    tags: Optional[Dict[str, str]] = None,
) -> network.PrivateEndpoint:
    """Create private endpoint"""

    if not hasattr(resource, "id"):
        raise ValueError("target resource must have an id attribute")

    if not hasattr(resource, "name"):
        raise ValueError("target resource must have a name attribute")

    if not hasattr(resource, "location"):
        raise ValueError("target resource must have a location attribute")

    subnet = private_endpoint_config.subnet

    # Determine if subnet is an object or a string (subnet ID)
    if isinstance(subnet, (network.Subnet, network.AwaitableGetSubnetResult)):
        subnet_id = subnet.id
    elif isinstance(subnet, str):
        subnet_id = subnet
    else:
        raise TypeError(
            "subnet must be either a network.Subnet object or a subnet ID string"
        )

    private_endpoint_name: str = (
        "pep-" + resource._name + "-" + private_endpoint_config.target_resource_type
    )

    private_endpoint: network.PrivateEndpoint = network.PrivateEndpoint(
        resource_name=private_endpoint_name,
        private_endpoint_name=private_endpoint_name,
        location=resource.location,
        resource_group_name=resource_group.name,
        subnet=network.SubnetArgs(id=subnet_id),
        private_link_service_connections=[
            network.PrivateLinkServiceConnectionArgs(
                name=private_endpoint_name,
                private_link_service_id=resource.id,
                group_ids=[private_endpoint_config.target_resource_type],
            )
        ],
        tags=tags,
    )

    # Create Private DNS record if Private DNS Zone is specified
    if private_endpoint_config.private_dns_zone_id:
        az_privatednszonegroup(
            resource=private_endpoint,
            resource_group=resource_group,
            target_resource_type=private_endpoint_config.target_resource_type,
            private_dns_zone=private_endpoint_config.private_dns_zone_id,
        )

    return private_endpoint

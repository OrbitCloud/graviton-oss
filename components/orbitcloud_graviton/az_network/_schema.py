from typing import List, Optional, Union

import pulumi
from pulumi_azure_native import network
from pydantic import BaseModel, ConfigDict, model_validator

from ._types import PrivateIPv4Network


class SubnetConfig(BaseModel):
    name: str
    address_prefix: PrivateIPv4Network
    delegation: Optional[str] = None
    private_endpoint_network_policies: network.VirtualNetworkPrivateEndpointNetworkPolicies = (
        network.VirtualNetworkPrivateEndpointNetworkPolicies.ENABLED
    )

    virtual_network_name: Optional[Union[str, pulumi.Output[str]]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class VnetConfig(BaseModel):
    address_space: List[PrivateIPv4Network]
    subnets: list[SubnetConfig]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Validate that subnets are unique, don't overlap and are within the vnet address space
    @model_validator(mode="after")
    def validate_subnets(m: "VnetConfig") -> "VnetConfig":
        subnet_address_prefixes: set[PrivateIPv4Network] = {subnet.address_prefix for subnet in m.subnets}
        if len(subnet_address_prefixes) != len(m.subnets):
            raise ValueError("Subnet address prefixes must be unique")

        if len(set(m.address_space)) != len(m.address_space):
            raise ValueError("Vnet address space must be unique")

        # Check if subnets are within at least one of the vnet address spaces
        for subnet in m.subnets:
            if not any(subnet.address_prefix.subnet_of(address_space) for address_space in m.address_space):
                raise ValueError(
                    f"Subnet {subnet.name} address prefix {subnet.address_prefix} is not within any of the vnet address spaces"
                )

            # Check if subnet overlaps with any other subnet
            if any(
                subnet.address_prefix.overlaps(other_subnet.address_prefix)
                for other_subnet in m.subnets
                if other_subnet != subnet
            ):
                raise ValueError(
                    f"Subnet {subnet.name} address prefix {subnet.address_prefix} overlaps with another subnet"
                )

        return m

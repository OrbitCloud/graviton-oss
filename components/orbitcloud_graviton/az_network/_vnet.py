from typing import List, Optional, Union

import pulumi
from pulumi import ComponentResource
from pulumi_azure_native.network import v20230901 as network
from pydantic import BaseModel, ConfigDict, model_validator

from orbitcloud_graviton.az_network._types import PrivateIPv4Network
from orbitcloud_graviton.pulumi_lib import AzureBase


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


class Vnet(ComponentResource):
    def __init__(
        self,
        stack: AzureBase,
        config: VnetConfig,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        self.stack: AzureBase = stack
        self.config = config

        super().__init__(
            "Graviton:az_network:Vnet",
            name=f"vnet-{self.stack.workload_name}",
            props=None,
            opts=opts,
        )
        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(opts, pulumi.ResourceOptions(parent=self))

        self.vnet = self._vnet()
        self.subnets = self._subnets()

        self._outputs()

    def _vnet(self) -> network.VirtualNetwork:
        return network.VirtualNetwork(
            self.stack.name_for(network.VirtualNetwork),
            args=network.VirtualNetworkArgs(
                resource_group_name=self.stack.resource_group.name,
                location=self.stack.location,
                address_space=network.AddressSpaceArgs(
                    address_prefixes=[str(x) for x in self.config.address_space],
                ),
            ),
            opts=self._opts._merge_instance(
                pulumi.ResourceOptions(ignore_changes=["subnets", "virtual_network_peerings"])
            ),
        )

    def _subnets(self) -> list[network.Subnet]:
        return [
            network.Subnet(
                resource_name=self.stack.name_for(network.Subnet, subnet.name),
                args=network.SubnetInitArgs(
                    resource_group_name=self.stack.resource_group.name,
                    virtual_network_name=self.vnet.name,
                    address_prefix=str(subnet.address_prefix),
                    delegations=self._subnet_delegation(subnet),
                    private_endpoint_network_policies=subnet.private_endpoint_network_policies,
                ),
                opts=pulumi.ResourceOptions(
                    parent=self.vnet,
                ),
            )
            for subnet in self.config.subnets
        ]

    def _subnet_delegation(self, subnet: SubnetConfig) -> list[network.DelegationArgs] | None:
        return (
            [
                (
                    network.DelegationArgs(
                        name=f"delegation-{subnet.name}-{subnet.delegation}",
                        service_name=subnet.delegation,
                    )
                )
            ]
            if subnet.delegation
            else None
        )

    def vhub_connection(
        self,
        virtual_hub: network.VirtualHub,
    ) -> network.HubVirtualNetworkConnection:
        """Creates a Virtual Network Connection in virtual hub"""
        hub_virtual_network_connection = network.HubVirtualNetworkConnection(
            self.stack.name_for(network.HubVirtualNetworkConnection, workload_name=f"vnet-{self.stack.workload_name}"),
            resource_group_name=self.stack.resource_group.name,
            enable_internet_security=True,
            remote_virtual_network=network.SubResourceArgs(
                id=self.vnet.id.apply(lambda id: f"{id}"),
            ),
            virtual_hub_name=virtual_hub.name,
            allow_hub_to_remote_vnet_transit=True,
            allow_remote_vnet_to_use_hub_vnet_gateways=True,
            # routing_configuration=network.RoutingConfigurationArgs(
            #     associated_route_table=network.SubResourceArgs(
            #         id=network.get_virtual_hub_route_table_v2(
            #             resource_group_name=rg.name,
            #             virtual_hub_name=vhub.name,
            #             route_table_name="defaultRouteTable",
            #         ).id,
            #     ),
            # ),
            # propagated_route_tables={
            #     "ids": [network.SubResourceArgs(
            #         id=network.get_virtual_hub_route_table_v2(
            #             resource_group_name=rg.name,
            #             virtual_hub_name=vhub.name,
            #             route_table_name="defaultRouteTable",
            #         ).id,
            #     )],
            # },
            opts=self._opts._merge_instance(pulumi.ResourceOptions(parent=self.vnet)),
        )
        return hub_virtual_network_connection

    def _outputs(self) -> None:
        self.register_outputs(
            {
                "vnet": self.vnet,
                "subnets": self.subnets,
            }
        )

        pulumi.export("vnet_id", self.vnet.id)
        pulumi.export(
            "subnets",
            self.vnet.subnets.apply(
                lambda args: {
                    f"{subnet.name}": {
                        "name": subnet.name,
                        "id": subnet.id,
                        "address_prefix": subnet.address_prefix,
                    }
                    for subnet in args
                }
            ),
        )

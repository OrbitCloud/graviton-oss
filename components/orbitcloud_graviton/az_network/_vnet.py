from typing import Optional

import pulumi
from pulumi import ComponentResource
from pulumi_azure_native import network

from orbitcloud_graviton.pulumi_lib import get_azure_stack

from ._schema import SubnetConfig, VnetConfig


class Vnet(ComponentResource):
    def __init__(
        self,
        config: VnetConfig,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        self.stack = get_azure_stack()
        super().__init__("Graviton:az_network:Vnet", name=self.stack.workload_name, props=None, opts=opts)

        self.config = config

        self.vnet = self._vnet()
        self.subnets = self._subnets()

        self._outputs()

    def _outputs(self) -> None:
        self.outputs = {
            "resource_group_name": self.stack.resource_group.name,
            "resource_group_id": self.stack.resource_group.id,
            "vnet": self.vnet,
            "subnets": self.subnets,
        }
        self.register_outputs(self.outputs)

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
            opts=pulumi.ResourceOptions(
                parent=self.stack.resource_group,
                # Workaround as pulumi thinks the subnets are to be removed
                # when they're not defined as a parameter to the vnet
                # https://github.com/pulumi/pulumi-azure-native/issues/3049
                ignore_changes=["subnets"],
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

    def _subnet_nsg(self, subnet: SubnetConfig) -> network.NetworkSecurityGroup:
        return network.NetworkSecurityGroup(
            resource_name=self.stack.name_for(network.NetworkSecurityGroup, subnet.name),
            # args=network.NetworkSecurityGroupInitArgs,
            opts=pulumi.ResourceOptions(
                parent=self.stack.resource_group,
            ),
        )

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

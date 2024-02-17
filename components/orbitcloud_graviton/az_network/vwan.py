from typing import List, Optional

import pulumi
from pulumi import ComponentResource
from pulumi_azure_native.network import v20230901 as network
from pydantic import BaseModel, ConfigDict, Field

from orbitcloud_graviton.az_lib.types import AzureIdRef
from orbitcloud_graviton.pulumi_lib import AzureBase

from .types import PrivateIPv4Network


class RemoteVirtualNetwork(BaseModel):
    connection_name: str
    remote_vnet_id: AzureIdRef
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class VirtualWanConfig(BaseModel):
    address_prefix: PrivateIPv4Network
    hub_vnet_connections: Optional[List[RemoteVirtualNetwork]] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class VirtualWan(ComponentResource):
    def __init__(
        self,
        stack: AzureBase,
        config: VirtualWanConfig,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        self.stack: AzureBase = stack
        self.config: VirtualWanConfig = config

        super().__init__(
            "Graviton:az_network:Vwan",
            name=f"vwan-{self.stack.workload_name}",
            props=None,
            opts=opts,
        )
        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts,
            pulumi.ResourceOptions(parent=self),
        )

        self.vwan: network.VirtualWan = self._vwan()
        self.vhub: network.VirtualHub = self._vhub()
        self.vhub_vnet_connections: List[
            network.HubVirtualNetworkConnection
        ] | None = self.vhub_vnet_connection()

        self._outputs()

    def _vwan(self) -> network.VirtualWan:
        return network.VirtualWan(
            resource_name=self.stack.name_for(network.VirtualWan),
            type="Standard",  # Basic or Standard – Standard is required for Point-to-Site VPN
            disable_vpn_encryption=False,
            allow_branch_to_branch_traffic=False,
            location=self.stack.location,
            resource_group_name=self.stack.resource_group.name,
            opts=self._opts,
        )

    def _vhub(self) -> network.VirtualHub:
        virtual_hub = network.VirtualHub(
            resource_name=self.stack.name_for(network.VirtualHub),
            address_prefix=str(self.config.address_prefix),
            location=self.stack.location,
            resource_group_name=self.stack.resource_group.name,
            sku="Standard",
            virtual_wan=network.SubResourceArgs(
                id=self.vwan.id.apply(lambda id: f"{id}"),
            ),
            opts=self._opts._merge_instance(
                pulumi.ResourceOptions(
                    ignore_changes=[
                        "virtual_router_ips",
                        "p2_s_vpn_gateway",
                    ]
                )
            ),
        )
        return virtual_hub

    def vhub_vnet_connection(
        self,
    ) -> List[network.HubVirtualNetworkConnection] | None:
        """Creates a Virtual Network Connection in virtual hub"""
        vnet_connections: List[network.HubVirtualNetworkConnection] = []

        if not self.config.hub_vnet_connections:
            return None

        for vnet in self.config.hub_vnet_connections:
            vnet_connections.append(
                network.HubVirtualNetworkConnection(
                    resource_name=self.stack.name_for(
                        resource_type=network.HubVirtualNetworkConnection,
                        workload_name=f"{vnet.connection_name}-{self.stack.workload_name}",
                    ),
                    resource_group_name=self.stack.resource_group.name,
                    enable_internet_security=True,
                    remote_virtual_network=network.SubResourceArgs(
                        id=vnet.remote_vnet_id,
                    ),
                    virtual_hub_name=self.vhub.name,
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
                    opts=self._opts._merge_instance(pulumi.ResourceOptions(parent=self.vhub)),
                )
            )
        return vnet_connections

    def _outputs(self) -> None:
        self.outputs = {
            "vwan": self.vwan,
            "vhub": self.vhub,
        }
        pulumi.export("vwan_id", self.vwan.id)
        pulumi.export("vwan_name", self.vwan.name)
        pulumi.export("vhub_id", self.vhub.id)
        pulumi.export("vhub_name", self.vhub.name)

        self.register_outputs(self.outputs)

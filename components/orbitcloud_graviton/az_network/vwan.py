from typing import Optional

import pulumi
from pulumi import ComponentResource
from pulumi_azure_native.network import v20230901 as network
from pydantic import BaseModel, ConfigDict

from orbitcloud_graviton.pulumi_lib import AzureBase

from .types import PrivateIPv4Network


class VirtualWanConfig(BaseModel):
    address_prefix: PrivateIPv4Network
    model_config = ConfigDict(arbitrary_types_allowed=True)


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

    def _vhub(self):
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

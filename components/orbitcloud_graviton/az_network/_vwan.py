from typing import Optional

import pulumi
from pulumi import ComponentResource
from pulumi_azure_native.network import v20230901 as network
from pydantic import BaseModel, ConfigDict

from orbitcloud_graviton.pulumi_lib import get_azure_stack

from ._types import PrivateIPv4Network


class VirtualWanConfig(BaseModel):
    address_prefix: PrivateIPv4Network
    model_config = ConfigDict(arbitrary_types_allowed=True)


class VirtualWan(ComponentResource):
    def __init__(
        self,
        config: VirtualWanConfig,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        self.stack = get_azure_stack()
        super().__init__("Graviton:az_network:Vwan", name=self.stack.workload_name, props=None, opts=opts)

        self.config = config

        self.vwan = self._vwan()
        self.vhub = self._vhub()

        self._outputs()

    def _outputs(self) -> None:
        self.outputs = {
            "resource_group_name": self.stack.resource_group.name,
            "resource_group_id": self.stack.resource_group.id,
        }
        self.register_outputs(self.outputs)

    def _vwan(self) -> network.VirtualWan:
        return network.VirtualWan(
            self.stack.name_for(network.VirtualWan),
            type="Standard",  # Basic or Standard – Standard is required for Point-to-Site VPN
            disable_vpn_encryption=False,
            allow_branch_to_branch_traffic=False,
            location=self.stack.location,
            resource_group_name=self.stack.resource_group.name,
        )

    def _vhub(self):
        virtual_hub = network.VirtualHub(
            self.stack.name_for(network.VirtualHub),
            address_prefix=str(self.config.address_prefix),
            location=self.stack.location,
            resource_group_name=self.stack.resource_group.name,
            sku="Standard",
            virtual_wan=network.SubResourceArgs(
                id=self.vwan.id.apply(lambda id: f"{id}"),
            ),
        )
        return virtual_hub

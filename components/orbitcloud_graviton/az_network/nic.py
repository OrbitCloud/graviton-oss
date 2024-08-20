from typing import Optional

import pulumi
from pulumi_azure_native.network import v20230901 as network
from pydantic import BaseModel, ConfigDict

from orbitcloud_graviton.az_lib.types import AzureIdRef
from orbitcloud_graviton.pulumi_lib import AzureStack


class NetworkInterfaceConfig(BaseModel):
    subnet_id: AzureIdRef
    accelerated_networking: bool = True
    ip_allocation: network.IPAllocationMethod = network.IPAllocationMethod.DYNAMIC

    log_workspace_id: Optional[AzureIdRef] = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class NetworkInterface:
    def __init__(
        self,
        stack: AzureStack,
        config: NetworkInterfaceConfig,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        self.stack: AzureStack = stack
        self.config: NetworkInterfaceConfig = config

        self._opts: pulumi.ResourceOptions | None = opts

        self.nic: network.NetworkInterface = self._nic()

        self._outputs()

    def _nic(self) -> network.NetworkInterface:
        return network.NetworkInterface(
            resource_name=self.stack.name_for(resource_type=network.NetworkInterface),
            args=network.NetworkInterfaceArgs(
                resource_group_name=self.stack.resource_group.name,
                enable_accelerated_networking=self.config.accelerated_networking,
                ip_configurations=[
                    network.NetworkInterfaceIPConfigurationArgs(
                        name="ipconfig1",
                        private_ip_allocation_method=self.config.ip_allocation,
                        subnet=network.SubnetArgs(id=self.config.subnet_id),
                    )
                ],
            ),
            opts=self._opts,
        )

    def _outputs(self) -> None:
        self.stack.export(
            exports={
                "nic": {
                    "id": self.nic.id,
                }
            }
        )

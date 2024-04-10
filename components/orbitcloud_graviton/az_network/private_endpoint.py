from typing import Any, Optional

import pulumi
from pulumi_azure_native.network import v20230901 as network
from pydantic import BaseModel, ConfigDict

from orbitcloud_graviton.az_lib.meta import AzureResourceMetadata, resource_meta
from orbitcloud_graviton.az_lib.types import AzureIdRef
from orbitcloud_graviton.pulumi_lib import AzureBase
from orbitcloud_graviton.pulumi_lib.types import DomainName


class PrivateEndpointConfig(BaseModel):
    subnet_id: AzureIdRef
    private_dns_zone_id: Optional[AzureIdRef] = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class PrivateEndpoint(pulumi.ComponentResource):
    def __init__(
        self,
        stack: AzureBase,
        config: PrivateEndpointConfig,
        target_resource: Any,
        target_resource_name: Optional[str] = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        self.stack: AzureBase = stack
        self.config: PrivateEndpointConfig = config

        super().__init__(
            "Graviton:PrivateEndpoint",
            name=f"pep-{target_resource._name}-{stack.env}",
            props=None,
            opts=pulumi.ResourceOptions.merge(
                opts1=opts, opts2=pulumi.ResourceOptions(parent=target_resource)
            ),
        )

        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts1=opts, opts2=pulumi.ResourceOptions(parent=self)
        )

        self.target_resource = target_resource
        self._target_meta: AzureResourceMetadata = resource_meta(obj=target_resource)

        # Validation
        if not self._target_meta.sub_resource_name or not self._target_meta.private_dns_zone:
            raise ValueError(
                f"Private Endpoint target resource {self.target_resource._name} does not have a target_resource_type defined in metadata."
            )

        self.target_type: str = self._target_meta.sub_resource_name
        self.target_dns_zone_name: DomainName = self._target_meta.private_dns_zone

        # Use target_resource_name if supplied else use the target_resource._name
        self.name: str = stack.name_for(
            resource_type=network.PrivateEndpoint,
            workload_name=target_resource_name or self.target_resource._name,
        )

        self.private_endpoint: network.PrivateEndpoint = self._private_endpoint()
        self.private_dns_zone_group: network.PrivateDnsZoneGroup | None = (
            self._private_dns_zone_group()
        )

        self._outputs()

    def _private_endpoint(self) -> network.PrivateEndpoint:
        return network.PrivateEndpoint(
            resource_name=self.name,
            args=network.PrivateEndpointArgs(
                private_endpoint_name=self.name,
                location=self.target_resource.location,
                resource_group_name=self.stack.resource_group.name,
                subnet=network.SubnetArgs(id=self.config.subnet_id),
                private_link_service_connections=[
                    network.PrivateLinkServiceConnectionArgs(
                        name=self.name,
                        private_link_service_id=self.target_resource.id,
                        group_ids=[self.target_type],
                    )
                ],
                custom_dns_configs=[],
            ),
            opts=self._opts,
        )

    def _private_dns_zone_group(self) -> network.PrivateDnsZoneGroup | None:
        if self.config.private_dns_zone_id:
            return network.PrivateDnsZoneGroup(
                resource_name=self.stack.name_for(resource_type=network.PrivateDnsZoneGroup),
                args=network.PrivateDnsZoneGroupArgs(
                    private_dns_zone_configs=[
                        network.PrivateDnsZoneConfigArgs(
                            private_dns_zone_id=self.config.private_dns_zone_id,
                            name=self.target_dns_zone_name,
                        )
                    ],
                    resource_group_name=self.stack.resource_group.name,
                    private_endpoint_name=self.name,
                ),
                opts=pulumi.ResourceOptions.merge(
                    self._opts,
                    pulumi.ResourceOptions(
                        parent=self.private_endpoint, deleted_with=self.private_endpoint
                    ),
                ),
            )

    def _outputs(self) -> None:
        self.register_outputs(
            outputs={"private_endpoint": self.private_endpoint},
        )

        self.stack.export(
            exports={
                "private_endpoint": {
                    "id": self.private_endpoint.id,
                    "name": self.private_endpoint.name,
                    "target_type": self.target_type,
                    "dns_zone": {
                        "name": self.target_dns_zone_name,
                        "id": self.config.private_dns_zone_id,
                    },
                }
            }
        )

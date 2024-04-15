from typing import Optional

import pulumi
from pulumi_azure_native import search
from pydantic import BaseModel, ConfigDict

from orbitcloud_graviton.az_network.private_endpoint import PrivateEndpoint, PrivateEndpointConfig
from orbitcloud_graviton.az_network.types import PublicIPv4Network
from orbitcloud_graviton.pulumi_lib import AzureStack


class SearchServiceConfig(BaseModel):
    partitions: Optional[int] = 1
    replicas: Optional[int] = 1
    sku: Optional[search.SkuName] = search.SkuName.STANDARD
    disable_local_auth: Optional[bool] = True
    public_network_access: Optional[search.PublicNetworkAccess] = (
        search.PublicNetworkAccess.DISABLED
    )
    allowed_public_ips: Optional[list[PublicIPv4Network]] = None
    private_endpoints: Optional[list[PrivateEndpointConfig]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class SearchService(pulumi.ComponentResource):
    def __init__(
        self,
        stack: AzureStack,
        config: SearchServiceConfig,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        self.stack: AzureStack = stack
        self.config: SearchServiceConfig = config

        super().__init__(
            "Graviton:Search",
            name=f"search-{stack.workload_name}-{stack.env}",
            props=None,
            opts=opts,
        )

        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts1=opts, opts2=pulumi.ResourceOptions(parent=self)
        )

        self.service: search.Service = self._service()
        self.private_endpoints: list[PrivateEndpoint] | None = self._private_endpoint()

        self._outputs()

    def _service(self) -> search.Service:
        return search.Service(
            resource_name=self.stack.name_for(resource_type=search.Service),
            args=search.ServiceArgs(
                sku=search.SkuArgs(name=self.config.sku),
                replica_count=self.config.replicas,
                partition_count=self.config.partitions,
                location=self.stack.location,
                resource_group_name=self.stack.resource_group.name,
                disable_local_auth=self.config.disable_local_auth,
                identity=search.IdentityArgs(type=search.IdentityType.SYSTEM_ASSIGNED),
                network_rule_set=search.NetworkRuleSetArgs(
                    ip_rules=[
                        search.IpRuleArgs(value=str(ip))
                        for ip in self.config.allowed_public_ips or []
                    ]
                ),
            ),
            opts=self._opts,
        )

    def _private_endpoint(self) -> list[PrivateEndpoint] | None:
        if self.config.private_endpoints:
            return [
                PrivateEndpoint(
                    stack=self.stack, config=pe, target_resource=self.service, opts=self._opts
                )
                for pe in self.config.private_endpoints
            ]

    def _outputs(self) -> None:
        self.register_outputs(
            outputs={"service": self.service},
        )

        self.stack.export(
            exports={
                "search_service": {
                    "id": self.service.id,
                    "name": self.service.name,
                }
            }
        )

from typing import List, Optional

import pulumi
from pulumi import ComponentResource
from pulumi_azure_native import eventhub
from pydantic import BaseModel, ConfigDict

from orbitcloud_graviton.pulumi_lib import AzureBase


class EventHubConfig(BaseModel):
    name: str
    partition_count: Optional[int] = 1
    retention_hours: Optional[int] = 1
    cleanup_policy: Optional[
        eventhub.CleanupPolicyRetentionDescription
    ] = eventhub.CleanupPolicyRetentionDescription.DELETE


class NamespaceConfig(BaseModel):
    disable_local_auth: Optional[bool] = False
    public_network_access: Optional[str] = eventhub.PublicNetworkAccess.DISABLED
    sku: eventhub.SkuArgs = eventhub.SkuArgs(name="Standard", tier="Standard")

    hubs: List[EventHubConfig]

    model_config = ConfigDict(arbitrary_types_allowed=True)


class EventHub(ComponentResource):
    def __init__(
        self,
        stack: AzureBase,
        config: NamespaceConfig,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        self.stack: AzureBase = stack
        super().__init__("Graviton:az_eventhub:EventHub", name=f"evh-{self.stack.workload_name}", props=None, opts=opts)
        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(opts, pulumi.ResourceOptions(parent=self))

        self.config: NamespaceConfig = config

        self.namespace: eventhub.Namespace = self._namespace()
        self.hubs: List[eventhub.EventHub] = self._eventhubs()

        self._outputs()

    def _namespace(self) -> eventhub.Namespace:
        return eventhub.Namespace(
            resource_name=self.stack.name_for(eventhub.Namespace),
            resource_group_name=self.stack.resource_group.name,
            location=self.stack.location,
            disable_local_auth=self.config.disable_local_auth,
            identity=eventhub.IdentityArgs(type=eventhub.ManagedServiceIdentityType.SYSTEM_ASSIGNED),
            is_auto_inflate_enabled=False,
            kafka_enabled=True,
            minimum_tls_version=eventhub.TlsVersion.TLS_VERSION_1_2,
            public_network_access=self.config.public_network_access,
            sku=self.config.sku,
            zone_redundant=True,
            opts=self._opts,
        )

    def _eventhubs(self) -> List[eventhub.EventHub]:
        return (
            [
                eventhub.EventHub(
                    resource_name=self.stack.name_for(eventhub.EventHub),
                    event_hub_name=self.stack.name_for(eventhub.EventHub),
                    resource_group_name=self.stack.resource_group.name,
                    namespace_name=self.namespace.name,
                    partition_count=hub.partition_count,
                    retention_description=eventhub.RetentionDescriptionArgs(
                        cleanup_policy=hub.cleanup_policy,
                        retention_time_in_hours=hub.retention_hours,
                    ),
                )
                for hub in self.config.hubs
            ]
            if self.config.hubs
            else []
        )

    def _outputs(self) -> None:
        self.register_outputs({})

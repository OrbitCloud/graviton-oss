from typing import List, Literal, Optional

import pulumi
from pulumi import ComponentResource
from pulumi_azure_native import eventhub as pul_eventhub
from pulumi_azure_native import insights
from pydantic import BaseModel, ConfigDict

from orbitcloud_graviton.az_lib.types import AzureIdRef
from orbitcloud_graviton.az_monitor.az_diagnosticsetting import diagnostic_setting
from orbitcloud_graviton.pulumi_lib import AzureBase


class EventHubConfig(BaseModel):
    name: str
    partition_count: Optional[int] = 1
    retention_hours: Optional[int] = 1
    cleanup_policy: Optional[
        pul_eventhub.CleanupPolicyRetentionDescription
    ] = pul_eventhub.CleanupPolicyRetentionDescription.DELETE


class NamespaceConfig(BaseModel):
    disable_local_auth: Optional[bool] = False
    public_network_access: Optional[str] = pul_eventhub.PublicNetworkAccess.DISABLED
    sku: Literal["Basic", "Standard", "Premium"] = "Standard"

    hubs: List[EventHubConfig]

    log_workspace_id: Optional[AzureIdRef] = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class EventHub(ComponentResource):
    def __init__(
        self,
        stack: AzureBase,
        config: NamespaceConfig,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        self.stack: AzureBase = stack
        self.config: NamespaceConfig = config

        super().__init__(
            "Graviton:az_eventhub:EventHub",
            name=f"evh-{self.stack.workload_name}",
            props=None,
            opts=opts,
        )
        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts, pulumi.ResourceOptions(parent=self)
        )

        self.namespace: pul_eventhub.Namespace = self._namespace()
        self.hubs: List[pul_eventhub.EventHub] = self._eventhubs()
        self._diagnostic_settings()

        self._outputs()

    def _namespace(self) -> pul_eventhub.Namespace:
        return pul_eventhub.Namespace(
            resource_name=self.stack.name_for(pul_eventhub.Namespace),
            resource_group_name=self.stack.resource_group.name,
            location=self.stack.location,
            disable_local_auth=self.config.disable_local_auth,
            identity=pul_eventhub.IdentityArgs(
                type=pul_eventhub.ManagedServiceIdentityType.SYSTEM_ASSIGNED
            ),
            is_auto_inflate_enabled=False,
            kafka_enabled=True,
            minimum_tls_version=pul_eventhub.TlsVersion.TLS_VERSION_1_2,
            public_network_access=self.config.public_network_access,
            sku=pul_eventhub.SkuArgs(
                name=self.config.sku,
                tier=self.config.sku,
            ),
            zone_redundant=True,
            opts=self._opts,
        )

    def _eventhubs(self) -> List[pul_eventhub.EventHub]:
        return (
            [
                pul_eventhub.EventHub(
                    resource_name=self.stack.name_for(pul_eventhub.EventHub),
                    event_hub_name=self.stack.name_for(pul_eventhub.EventHub),
                    resource_group_name=self.stack.resource_group.name,
                    namespace_name=self.namespace.name,
                    partition_count=hub.partition_count,
                    retention_description=pul_eventhub.RetentionDescriptionArgs(
                        cleanup_policy=hub.cleanup_policy,
                        retention_time_in_hours=hub.retention_hours,
                    ),
                )
                for hub in self.config.hubs
            ]
            if self.config.hubs
            else []
        )

    def _diagnostic_settings(self) -> insights.DiagnosticSetting | None:
        if self.config.log_workspace_id:
            return diagnostic_setting(
                resource=self.namespace,
                log_workspace_id=self.config.log_workspace_id,
                metric_categories=["AllMetrics"],
                log_categories=[
                    "ApplicationMetricsLogs",
                    "ArchiveLogs",
                    "AutoScaleLogs",
                    "CustomerManagedKeyUserLogs",
                    "EventHubVNetConnectionEvent",
                    "KafkaCoordinatorLogs",
                    "KafkaUserErrorLogs",
                    "OperationalLogs",
                    "RuntimeAuditLogs",
                ],
                opts=pulumi.ResourceOptions(parent=self.namespace),
            )

    def _outputs(self) -> None:
        self.register_outputs(
            {
                "namespace": self.namespace,
                "hubs": self.hubs,
            }
        )
        pulumi.export("eventhub_endpoint", self.namespace.service_bus_endpoint)
        pulumi.export("eventhub_namespace_id", self.namespace.id)
        pulumi.export("eventhub_namespace_name", self.namespace.name)

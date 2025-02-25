from typing import Literal

import pulumi
from pulumi import ComponentResource
from pulumi_azure_native import eventhub as pul_eventhub
from pulumi_azure_native import insights
from pydantic import BaseModel, ConfigDict

from orbitcloud_graviton.az_lib.types import AzureIdRef
from orbitcloud_graviton.az_monitor import diagnostic_setting
from orbitcloud_graviton.az_network import PrivateEndpoint, PrivateEndpointConfig, PublicIPv4Network
from orbitcloud_graviton.pulumi_lib import AzureStack


class EventHubConfig(BaseModel):
    name: str
    partitions: int | None = 1
    retention_hours: int | None = 1
    cleanup_policy: pul_eventhub.CleanupPolicyRetentionDescription | None = (
        pul_eventhub.CleanupPolicyRetentionDescription.DELETE
    )

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class NamespaceScaling(BaseModel):
    min: int | None = 1
    max: int | None = None
    auto: bool | None = False


class NamespaceConfig(BaseModel):
    name: str | None = None
    disable_local_auth: bool | None = False
    public_network_access: str | None = pul_eventhub.PublicNetworkAccess.DISABLED
    sku: Literal["Basic", "Standard", "Premium"] = "Standard"

    hubs: list[EventHubConfig] | None = None
    scaling: NamespaceScaling = NamespaceScaling()

    allowed_public_ips: list[PublicIPv4Network] | None = None
    allowed_subnet_ids: list[AzureIdRef] | None = None
    allow_azure_services: bool | None = True

    private_endpoints: list[PrivateEndpointConfig] | None = None

    log_workspace_id: AzureIdRef | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class EventHub(ComponentResource):
    def __init__(
        self,
        stack: AzureStack,
        config: NamespaceConfig,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        self.stack: AzureStack = stack
        self.config: NamespaceConfig = config

        super().__init__(
            "Graviton:az_eventhub:EventHub",
            name=f"evh-{self.stack.workload_name}",
            props=None,
            opts=opts,
        )
        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts1=opts, opts2=pulumi.ResourceOptions(parent=self)
        )

        self.namespace: pul_eventhub.Namespace = self._namespace()
        self.hubs: dict[str, pul_eventhub.EventHub] = self._eventhubs()
        self.network_rules: pul_eventhub.NamespaceNetworkRuleSet | None = self._network_rules()
        self.private_endpoints: list[PrivateEndpoint] | None = self._private_endpoints()
        self._diagnostic_settings()

        self._outputs()

    def _namespace(self) -> pul_eventhub.Namespace:
        return pul_eventhub.Namespace(
            resource_name=self.stack.name_for(resource_type=pul_eventhub.Namespace),
            resource_group_name=self.stack.resource_group.name,
            location=self.stack.location,
            disable_local_auth=self.config.disable_local_auth,
            identity=pul_eventhub.IdentityArgs(
                type=pul_eventhub.ManagedServiceIdentityType.SYSTEM_ASSIGNED
            ),
            is_auto_inflate_enabled=self.config.scaling.auto,
            maximum_throughput_units=self.config.scaling.max,
            kafka_enabled=True,
            minimum_tls_version=pul_eventhub.TlsVersion.TLS_VERSION_1_2,
            public_network_access=self.config.public_network_access,
            sku=pul_eventhub.SkuArgs(
                name=self.config.sku,
                tier=self.config.sku,
                capacity=self.config.scaling.min,
            ),
            zone_redundant=True,
            opts=pulumi.ResourceOptions.merge(
                opts1=self._opts,
                opts2=pulumi.ResourceOptions(ignore_changes=["private_endpoint_connections"]),
            ),
        )

    def _eventhubs(self) -> dict[str, pul_eventhub.EventHub]:
        return {
            hub.name: pul_eventhub.EventHub(
                resource_name=self.stack.name_for(
                    resource_type=pul_eventhub.EventHub, workload_name=hub.name
                ),
                event_hub_name=hub.name,
                resource_group_name=self.stack.resource_group.name,
                namespace_name=self.namespace.name,
                partition_count=hub.partitions,
                retention_description=pul_eventhub.RetentionDescriptionArgs(
                    cleanup_policy=hub.cleanup_policy,
                    retention_time_in_hours=hub.retention_hours,
                ),
                opts=pulumi.ResourceOptions.merge(
                    opts1=self._opts, opts2=pulumi.ResourceOptions(parent=self.namespace)
                ),
            )
            for hub in self.config.hubs or []
        }

    def _network_rules(self) -> pul_eventhub.NamespaceNetworkRuleSet | None:
        if not self.config.allowed_public_ips and not self.config.allowed_subnet_ids:
            return None

        return pul_eventhub.NamespaceNetworkRuleSet(
            resource_name=self.stack.name_for(resource_type=pul_eventhub.NamespaceNetworkRuleSet),
            args=pul_eventhub.NamespaceNetworkRuleSetArgs(
                namespace_name=self.namespace.name,
                resource_group_name=self.stack.resource_group.name,
                default_action="Deny",
                public_network_access=self.config.public_network_access,
                ip_rules=[
                    pul_eventhub.NWRuleSetIpRulesArgs(
                        action=pul_eventhub.NetworkRuleIPAction.ALLOW,
                        ip_mask=str(object=ip),
                    )
                    for ip in self.config.allowed_public_ips or []
                ],
                virtual_network_rules=[
                    pul_eventhub.NWRuleSetVirtualNetworkRulesArgs(
                        ignore_missing_vnet_service_endpoint=False,
                        subnet=pul_eventhub.SubnetArgs(id=ref),
                    )
                    for ref in self.config.allowed_subnet_ids or []
                ],
                trusted_service_access_enabled=self.config.allow_azure_services,
            ),
            opts=self._opts,
        )

    def _private_endpoints(self) -> list[PrivateEndpoint] | None:
        if self.config.private_endpoints:
            return [
                PrivateEndpoint(
                    stack=self.stack,
                    config=endpoint,
                    target_resource=self.namespace,
                    opts=self._opts,
                )
                for endpoint in self.config.private_endpoints
            ]

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

        self.stack.export(
            exports={
                "eventhub": {
                    "namespace": {
                        "id": self.namespace.id,
                        "name": self.namespace.name,
                        "endpoint": self.namespace.private_endpoint_connections,
                    },
                    "hubs": {
                        name: {
                            "name": hub.name,
                            "partitions": hub.partition_count,
                            "retention": hub.message_retention_in_days,
                        }
                        for name, hub in self.hubs.items()
                    },
                }
            }
        )

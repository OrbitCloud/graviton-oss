import pulumi
from pulumi_azure_native import monitor
from pulumi_azure_native import servicebus as sb
from pydantic import BaseModel, ConfigDict

from orbitcloud_graviton.az_lib.types import AzureIdRef
from orbitcloud_graviton.az_monitor import diagnostic_setting
from orbitcloud_graviton.az_network import PrivateEndpoint, PrivateEndpointConfig
from orbitcloud_graviton.az_network.types import PublicIPv4Network
from orbitcloud_graviton.pulumi_lib import AzureStack


class ServiceBusQueueConfig(BaseModel):
    name: str
    partitioning: bool = False

    max_size_mb: int = 1024

    enable_batched_operations: bool = True
    enable_express: bool = False

    default_message_time_to_live: str = "P14D"  # ISO 8601 duration
    dead_lettering_on_message_expiration: bool = True
    forward_dead_letters_to: str | None = None
    lock_duration: str = "PT1M"  # ISO 8601 duration

    requires_duplicate_detection: bool = False
    duplicate_detection_window: str = "PT10M"  # ISO 8601 duration

    max_delivery_count: int = 10
    requires_session: bool = False
    forward_to: str | None = None
    auto_delete_on_idle: str | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ServiceBusNamespaceConfig(BaseModel):
    name: str | None = None
    sku: sb.SkuName = sb.SkuName.STANDARD
    capacity: int | None = 1
    zone_redundant: bool = False
    minimum_tls_version: str = "1.2"
    public_network_access: sb.PublicNetworkAccess = sb.PublicNetworkAccess.DISABLED
    disable_local_auth: bool = True
    queues: list[ServiceBusQueueConfig] | None = None

    allow_azure_services: bool = True

    # Add private endpoint configuration
    private_endpoints: list[PrivateEndpointConfig] | None = None

    log_workspace_id: AzureIdRef | None = None

    allowed_public_ips: list[PublicIPv4Network] | None = None
    allowed_subnet_ids: list[AzureIdRef] | None = None
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ServiceBus(pulumi.ComponentResource):
    def __init__(
        self,
        stack: AzureStack,
        config: ServiceBusNamespaceConfig,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        self.stack: AzureStack = stack
        self.config: ServiceBusNamespaceConfig = config

        super().__init__(
            "Graviton:ServiceBus",
            name=f"servicebus-{stack.workload_name}-{stack.env}",
            props=None,
            opts=opts,
        )

        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts1=opts, opts2=pulumi.ResourceOptions(parent=self)
        )

        self.namespace: sb.Namespace = self._servicebus()
        self.queues: dict[str, sb.Queue] = self._queues()
        self.private_endpoints: list[PrivateEndpoint] | None = self._private_endpoints()
        self.diagnostic_settings: monitor.DiagnosticSetting | None = self._diagnostic_settings()
        self.ip_filter_rules: sb.NamespaceNetworkRuleSet | None = self._ip_filter_rules()

        self._outputs()

    def _servicebus(self) -> sb.Namespace:
        return sb.Namespace(
            resource_name=self.stack.name_for(resource_type=sb.Namespace),
            args=sb.NamespaceArgs(
                namespace_name=self.config.name,
                location=self.stack.location,
                resource_group_name=self.stack.resource_group.name,
                sku=sb.SBSkuArgs(
                    name=self.config.sku,
                    capacity=self.config.capacity,
                ),
                minimum_tls_version=self.config.minimum_tls_version,
                public_network_access=self.config.public_network_access,
                disable_local_auth=self.config.disable_local_auth,
                zone_redundant=self.config.zone_redundant,
                tags=self.stack.tags,
            ),
            opts=self._opts,
        )

    def _queues(self) -> dict[str, sb.Queue]:
        queues = {}
        if self.config.queues:
            for queue_config in self.config.queues:
                queues[queue_config.name] = sb.Queue(
                    resource_name=self.stack.name_for(
                        resource_type=sb.Queue, workload_name=queue_config.name
                    ),
                    args=sb.QueueArgs(
                        namespace_name=self.namespace.name,
                        queue_name=queue_config.name,
                        resource_group_name=self.stack.resource_group.name,
                        enable_partitioning=queue_config.partitioning,
                        max_size_in_megabytes=queue_config.max_size_mb,
                        enable_batched_operations=queue_config.enable_batched_operations,
                        enable_express=queue_config.enable_express,
                        dead_lettering_on_message_expiration=queue_config.dead_lettering_on_message_expiration,
                        default_message_time_to_live=queue_config.default_message_time_to_live,
                        duplicate_detection_history_time_window=queue_config.duplicate_detection_window,
                        lock_duration=queue_config.lock_duration,
                        max_delivery_count=queue_config.max_delivery_count,
                        requires_duplicate_detection=queue_config.requires_duplicate_detection,
                        requires_session=queue_config.requires_session,
                        forward_to=queue_config.forward_to,
                        forward_dead_lettered_messages_to=queue_config.forward_dead_letters_to,
                        auto_delete_on_idle=queue_config.auto_delete_on_idle,
                    ),
                    opts=pulumi.ResourceOptions(parent=self.namespace),
                )
        return queues

    def _private_endpoints(self) -> list[PrivateEndpoint] | None:
        return [
            PrivateEndpoint(
                stack=self.stack,
                target_resource=self.namespace,
                config=endpoint_config,
                opts=pulumi.ResourceOptions(parent=self.namespace),
            )
            for endpoint_config in self.config.private_endpoints or []
        ]

    def _diagnostic_settings(self) -> monitor.DiagnosticSetting | None:
        if self.config.log_workspace_id:
            return diagnostic_setting(
                resource=self.namespace,
                log_workspace_id=self.config.log_workspace_id,
                metric_categories=["AllMetrics"],
                log_categories=[
                    "OperationalLogs",
                    "RuntimeAuditLogs",
                    "ApplicationMetricsLogs",
                    "VNetAndIPFilteringLogs",
                ],
                opts=pulumi.ResourceOptions(parent=self.namespace),
            )

    def _ip_filter_rules(self) -> sb.NamespaceNetworkRuleSet | None:
        if not self.config.allowed_public_ips:
            return None

        return sb.NamespaceNetworkRuleSet(
            resource_name=self.stack.name_for(resource_type=sb.NamespaceNetworkRuleSet),
            args=sb.NamespaceNetworkRuleSetArgs(
                namespace_name=self.namespace.name,
                resource_group_name=self.stack.resource_group.name,
                default_action=sb.DefaultAction.DENY,
                ip_rules=[
                    sb.NWRuleSetIpRulesArgs(
                        ip_mask=str(ip),
                        action=sb.NetworkRuleIPAction.ALLOW,
                    )
                    for ip in self.config.allowed_public_ips
                ],
                virtual_network_rules=[
                    sb.NWRuleSetVirtualNetworkRulesArgs(
                        ignore_missing_vnet_service_endpoint=False,
                        subnet=sb.SubnetArgs(id=subnet),
                    )
                    for subnet in self.config.allowed_subnet_ids or []
                ],
                trusted_service_access_enabled=self.config.allow_azure_services,
            ),
            opts=pulumi.ResourceOptions(parent=self.namespace),
        )

    def _outputs(self) -> None:
        self.register_outputs(
            {
                "namespace": self.namespace,
                "queues": self.queues,
                "private_endpoints": self.private_endpoints,
            }
        )

        self.stack.export(
            exports={
                "servicebus": {
                    "namespace": {
                        "id": self.namespace.id,
                        "name": self.namespace.name,
                    },
                    "queues": {
                        name: {
                            "name": queue.name,
                            "partitioning": queue.enable_partitioning,
                        }
                        for name, queue in self.queues.items()
                    },
                }
            }
        )

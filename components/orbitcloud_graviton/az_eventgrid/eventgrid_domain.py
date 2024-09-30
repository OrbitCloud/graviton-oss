from typing import List, Optional, Union

import pulumi
from pulumi_azure_native import eventgrid, insights
from pydantic import BaseModel, ConfigDict

from orbitcloud_graviton.az_iam.assignment import IamAssignmentConfig, iam_assignment
from orbitcloud_graviton.az_lib.types import AzureIdRef, StrRef
from orbitcloud_graviton.az_monitor import diagnostic_setting
from orbitcloud_graviton.az_network import PrivateEndpoint, PrivateEndpointConfig
from orbitcloud_graviton.az_network.types import PrivateIPv4Network, PublicIPv4Network
from orbitcloud_graviton.pulumi_lib import AzureStack


class EventGridDomainConfig(BaseModel):
    name: Optional[str] = None
    disable_local_auth: Optional[bool] = True

    data_residency: eventgrid.DataResidencyBoundary = eventgrid.DataResidencyBoundary.WITHIN_REGION
    input_schema: eventgrid.InputSchema = eventgrid.InputSchema.EVENT_GRID_SCHEMA

    # Topic properties
    auto_delete_topic_with_last_subscription: Optional[bool] = False
    auto_create_topic_with_first_subscription: Optional[bool] = False
    topics: Optional[List[str]] = None

    # Networking
    public_network_access: Optional[bool] = False
    inbound_ip_rules: Optional[List[Union[PublicIPv4Network, PrivateIPv4Network, StrRef]]] = None
    private_endpoints: Optional[List[PrivateEndpointConfig]] = None

    log_workspace_id: Optional[AzureIdRef] = None
    azure_permissions: list[IamAssignmentConfig] | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class EventGridDomain(pulumi.ComponentResource):
    def __init__(
        self,
        stack: AzureStack,
        config: EventGridDomainConfig,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        self.stack: AzureStack = stack
        self.config: EventGridDomainConfig = config

        super().__init__(
            "Graviton:EventGridDomain",
            name=f"evgd-{stack.workload_name}-{stack.env}",
            props=None,
            opts=opts,
        )

        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts1=opts, opts2=pulumi.ResourceOptions(parent=self)
        )

        self.eventgrid_domain: eventgrid.Domain = self._eventgrid_domain()
        self.topics: dict[str, eventgrid.DomainTopic] = self._eventgrid_topics()
        self._azure_permissions()
        self.diagnostic_settings: insights.DiagnosticSetting | None = self._diagnostic_settings()

        self._outputs()

    def _eventgrid_domain(self) -> eventgrid.Domain:
        return eventgrid.Domain(
            resource_name=self.stack.name_for(
                resource_type=eventgrid.Domain,
                workload_name=self.config.name or self.stack.workload_name,
            ),
            args=eventgrid.DomainArgs(
                domain_name=self.stack.name_for(
                    resource_type=eventgrid.Domain,
                    workload_name=self.config.name or self.stack.workload_name,
                ),
                resource_group_name=self.stack.resource_group.name,
                location=self.stack.resource_group.location,
                identity=eventgrid.IdentityInfoArgs(type=eventgrid.IdentityType.SYSTEM_ASSIGNED),
                inbound_ip_rules=self._eventgrid_domain_ip_rules(),
            ),
            opts=self._opts,
        )

    def _eventgrid_domain_ip_rules(self) -> List[eventgrid.InboundIpRuleArgs]:
        return (
            [
                eventgrid.InboundIpRuleArgs(action="Allow", ip_mask=str(ip))
                for ip in self.config.inbound_ip_rules
            ]
            if self.config.inbound_ip_rules
            else []
        )

    def _eventgrid_topics(self) -> dict[str, eventgrid.DomainTopic]:
        return {
            topic: eventgrid.DomainTopic(
                resource_name=self.stack.name_for(
                    resource_type=eventgrid.DomainTopic, workload_name=topic
                ),
                args=eventgrid.DomainTopicArgs(
                    domain_name=self.eventgrid_domain.name,
                    domain_topic_name=topic,
                    resource_group_name=self.stack.resource_group.name,
                ),
                opts=self._opts,
            )
            for topic in self.config.topics or []
        }

    def _private_endpoint(self) -> list[PrivateEndpoint] | None:
        if self.config.private_endpoints:
            return [
                PrivateEndpoint(
                    stack=self.stack,
                    config=pe,
                    target_resource=self.eventgrid_domain,
                    opts=self._opts,
                )
                for pe in self.config.private_endpoints
            ]

    def _azure_permissions(self) -> None:
        if self.config.azure_permissions:
            for perm in self.config.azure_permissions:
                iam_assignment(
                    stack=self.stack,
                    config=IamAssignmentConfig(
                        name_prefix=f"{perm.name_prefix}-{self.config.name}"
                        if perm.name_prefix
                        else self.config.name,
                        role=perm.role,
                        scope=perm.scope,
                        description=perm.description,
                    ),
                    principal_id=self.eventgrid_domain.identity.principal_id,
                    opts=pulumi.ResourceOptions(
                        parent=self.eventgrid_domain, delete_before_replace=True
                    ),
                )

    def _diagnostic_settings(self) -> insights.DiagnosticSetting | None:
        if self.config.log_workspace_id:
            return diagnostic_setting(
                resource=self.eventgrid_domain,
                log_workspace_id=self.config.log_workspace_id,
                metric_categories=["AllMetrics"],
                log_categories=[
                    "DataPlaneRequests",
                    "DeliveryFailures",
                    "PublishFailures",
                ],
                opts=pulumi.ResourceOptions(parent=self.eventgrid_domain),
            )

    def _outputs(self) -> None:
        self.register_outputs(
            {"eventgrid_domain": self.eventgrid_domain},
        )

        self.stack.export(
            exports={
                "eventgrid_domain": {
                    "id": self.eventgrid_domain.id,
                    "name": self.eventgrid_domain.name,
                    "endpoint": self.eventgrid_domain.endpoint,
                    "topics": {
                        name: {
                            "name": topic.name,
                        }
                        for name, topic in self.topics.items()
                    },
                }
            }
        )

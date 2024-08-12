from ipaddress import IPv4Address
from typing import List, Literal, Optional

import pulumi
from pulumi import ComponentResource
from pulumi_azure_native.network import v20220701 as network
from pydantic import BaseModel, ConfigDict, Field, model_validator

from orbitcloud_graviton.az_lib.types import AzureIdRef, AzureResourceId
from orbitcloud_graviton.pulumi_lib import AzureStack
from orbitcloud_graviton.pulumi_lib.helpers import fmt_name
from orbitcloud_graviton.pulumi_lib.types import DomainName


class ResolverInboundEndpoint(BaseModel):
    subnet_id: AzureIdRef = Field(
        default=None,
        title="Inbound Endpoint Subnet",
        description="The subnet to be used for the Inbound Endpoint. The subnet must be in the same virtual network as the DNS Resolver.",
        examples=[
            "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-name/providers/Microsoft.Network/virtualNetworks/vnet-name/subnets/subnet-name"
            "stack://project/stack-name/output-name",
            "stack://project/stack-name/output-name.subnet_id",
            "stack://project/stack-name/output-name.subnets.subnet_id",
        ],
    )

    private_ip_address: Optional[IPv4Address] = Field(
        default=None,
        title="Private IP Address",
        description="Statically assign Endpoint IP Address. If not specified, IP Allocation Method will be 'Dynamic'.",
    )

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ForwardingRuleConfig(BaseModel):
    rule_state: Literal["Enabled", "Disabled"] = "Enabled"
    domain_name: DomainName = Field(
        title="Domain Name",
        description="The domain name to be forwarded.",
        examples=["int.mydomain.local"],
    )
    target_dns_servers: List[IPv4Address] = Field(
        title="Target DNS Servers",
        description="The target DNS servers to forward the requests to.",
        examples=["- 10.243.1.10", "- 10.243.1.11"],
    )

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ResolverOutboundEndpoint(BaseModel):
    subnet_id: AzureIdRef = Field(
        default=None,
        title="Outbound Endpoint Subnet",
        description="The subnet to be used for the Outbound Endpoint. The subnet must be in the same virtual network as the DNS Resolver.",
        examples=[
            "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-name/providers/Microsoft.Network/virtualNetworks/vnet-name/subnets/subnet-name"
            "stack://project/stack-name/output-name",
            "stack://project/stack-name/output-name.subnet_id",
            "stack://project/stack-name/output-name.subnets.subnet_id",
        ],
    )
    rules: Optional[List[ForwardingRuleConfig]] = Field(
        default=None,
        title="Forwarding Rules",
        description="The forwarding rules to be used for the Outbound Endpoint.",
    )
    linked_vnets: Optional[List[AzureIdRef]] = Field(
        default=None,
        title="Linked Virtual Networks",
        description="The VNET(s) that will be able to utilize the Outbound Endpoint.",
        examples=[
            "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-name/providers/Microsoft.Network/virtualNetworks/vnet-name"
            "stack://project/stack-name/vnet.id",
        ],
    )

    @model_validator(mode="after")
    def validate_rules(m: "ResolverOutboundEndpoint") -> "ResolverOutboundEndpoint":
        if m.rules and not m.linked_vnets:
            raise ValueError("At least one linked VNET should be specified.")
        if m.linked_vnets and not m.rules:
            pulumi.warn(
                "Linked VNET(s) are specified but no forwarding rules are defined. Ignoring linked VNET(s)."
            )
        return m

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class PrivateDnsResolverConfig(BaseModel):
    virtual_network: AzureIdRef = Field(
        default=None,
        title="Virtual Network",
        description="The virtual network to be used for the Private DNS Resolver.",
        examples=[
            "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-name/providers/Microsoft.Network/virtualNetworks/vnet-name",
            "stack://project/stack-name/output-name",
            "stack://project/stack-name/output-name.vnet_id",
        ],
    )
    inbound_endpoint: Optional[ResolverInboundEndpoint] = Field(
        default=None,
        title="Inbound Endpoint",
        description="Inbound endpoint to be used for the Private DNS Resolver.",
    )
    outbound_endpoint: Optional[ResolverOutboundEndpoint] = Field(
        default=None,
        title="Outbound Endpoint",
        description="Outbound endpoint to be used for the Private DNS Resolver.",
    )
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class PrivateDnsResolver(ComponentResource):
    def __init__(
        self,
        stack: AzureStack,
        config: PrivateDnsResolverConfig,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        self.stack: AzureStack = stack
        self.config: PrivateDnsResolverConfig = config

        super().__init__(
            "Graviton:az_network:PrivateDnsResolver",
            name=f"pdnsr-{self.stack.workload_name}",
            props=None,
            opts=opts,
        )

        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts1=opts, opts2=pulumi.ResourceOptions(parent=self)
        )
        self.resolver: network.DnsResolver = self._resolver()
        self._outputs()

    def _resolver(self) -> network.DnsResolver:
        vnet = AzureResourceId(str(self.config.virtual_network))
        resolver = network.DnsResolver(
            resource_name=self.stack.name_for(resource_type=network.DnsResolver),
            dns_resolver_name=self.stack.name_for(resource_type=network.DnsResolver),
            location=self.stack.location,
            resource_group_name=self.stack.resource_group.name,
            virtual_network=network.SubResourceArgs(id=vnet.id),
        )

        if self.config.inbound_endpoint:
            network.InboundEndpoint(
                resource_name=self.stack.name_for(
                    resource_type=network.InboundEndpoint,
                ),
                inbound_endpoint_name=self.stack.name_for(
                    resource_type=network.InboundEndpoint,
                ),
                dns_resolver_name=resolver.name,
                location=self.stack.location,
                ip_configurations=[
                    network.InboundEndpointIPConfigurationArgs(
                        private_ip_allocation_method="Static"
                        if self.config.inbound_endpoint.private_ip_address
                        else "Dynamic",
                        subnet=network.SubResourceArgs(
                            id=AzureResourceId(str(self.config.inbound_endpoint.subnet_id)).id
                        ),
                        private_ip_address=str(self.config.inbound_endpoint.private_ip_address)
                        if self.config.inbound_endpoint.private_ip_address
                        else None,
                    )
                ],
                resource_group_name=self.stack.resource_group.name,
            )

        if self.config.outbound_endpoint:
            outboundEndpoint = network.OutboundEndpoint(
                resource_name=self.stack.name_for(
                    resource_type=network.OutboundEndpoint,
                ),
                outbound_endpoint_name=self.stack.name_for(
                    resource_type=network.OutboundEndpoint,
                ),
                dns_resolver_name=resolver.name,
                location=self.stack.location,
                resource_group_name=self.stack.resource_group.name,
                subnet=network.SubResourceArgs(
                    id=AzureResourceId(str(self.config.outbound_endpoint.subnet_id)).id
                ),
            )
            if self.config.outbound_endpoint.rules:
                ruleset = network.DnsForwardingRuleset(
                    resource_name=self.stack.name_for(
                        resource_type=network.DnsForwardingRuleset,
                    ),
                    dns_forwarding_ruleset_name=self.stack.name_for(
                        resource_type=network.DnsForwardingRuleset,
                    ),
                    dns_resolver_outbound_endpoints=[
                        network.SubResourceArgs(id=outboundEndpoint.id)
                    ],
                    location=self.stack.location,
                    resource_group_name=self.stack.resource_group.name,
                )
                for rule in self.config.outbound_endpoint.rules:
                    targets: List[network.TargetDnsServerArgsDict] = [
                        network.TargetDnsServerArgsDict({"ip_address": str(ip)})
                        for ip in rule.target_dns_servers
                    ]
                    network.ForwardingRule(
                        resource_name=fmt_name(rule.domain_name),
                        forwarding_rule_name=fmt_name(rule.domain_name),
                        resource_group_name=self.stack.resource_group.name,
                        forwarding_rule_state=rule.rule_state,
                        dns_forwarding_ruleset_name=ruleset.name,
                        domain_name=rule.domain_name + ".",
                        target_dns_servers=targets,
                    )
                if self.config.outbound_endpoint.linked_vnets:
                    for vnet in self.config.outbound_endpoint.linked_vnets:
                        v = AzureResourceId(str(vnet))
                        network.PrivateResolverVirtualNetworkLink(
                            resource_name=f"{v.resource_name}-link",  # type: ignore
                            virtual_network_link_name=f"{v.resource_name}-link",
                            dns_forwarding_ruleset_name=ruleset.name,
                            resource_group_name=self.stack.resource_group.name,
                            virtual_network=network.SubResourceArgs(id=v.id),
                        )

        return resolver

    def _outputs(self) -> None:
        self.register_outputs(
            outputs={
                "private_dns_resolver": self.resolver,
            }
        )
        self.stack.export(
            exports={
                "private_dns_resolver": {
                    "id": self.resolver.id,
                    "name": self.resolver.name,
                }
            }
        )

from ipaddress import IPv4Address
from typing import Literal

import pulumi
from pulumi import ComponentResource
from pulumi_azure_native import dnsresolver
from pydantic import BaseModel, ConfigDict, Field, model_validator

from orbitcloud_graviton.az_lib.types import AzureIdRef, AzureResourceId
from orbitcloud_graviton.pulumi_lib import AzureStack
from orbitcloud_graviton.pulumi_lib.helpers import fmt_name
from orbitcloud_graviton.pulumi_lib.types import DomainName


class ResolverInboundEndpoint(BaseModel):
    subnet_id: AzureIdRef = Field(
        ...,
        title="Inbound Endpoint Subnet",
        description="The subnet to be used for the Inbound Endpoint. The subnet must be in the same virtual network as the DNS Resolver.",
        examples=[
            "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-name/providers/Microsoft.Network/virtualNetworks/vnet-name/subnets/subnet-name"
            "stack://project/stack-name/output-name",
            "stack://project/stack-name/output-name.subnet_id",
            "stack://project/stack-name/output-name.subnets.subnet_id",
        ],
    )

    private_ip_address: IPv4Address | None = Field(
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
    target_dns_servers: list[IPv4Address] = Field(
        title="Target DNS Servers",
        description="The target DNS servers to forward the requests to.",
        examples=["- 10.243.1.10", "- 10.243.1.11"],
    )

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ResolverOutboundEndpoint(BaseModel):
    subnet_id: AzureIdRef = Field(
        default=...,
        title="Outbound Endpoint Subnet",
        description="The subnet to be used for the Outbound Endpoint. The subnet must be in the same virtual network as the DNS Resolver.",
        examples=[
            "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-name/providers/Microsoft.Network/virtualNetworks/vnet-name/subnets/subnet-name"
            "stack://project/stack-name/output-name",
            "stack://project/stack-name/output-name.subnet_id",
            "stack://project/stack-name/output-name.subnets.subnet_id",
        ],
    )
    rules: list[ForwardingRuleConfig] | None = Field(
        default=None,
        title="Forwarding Rules",
        description="The forwarding rules to be used for the Outbound Endpoint.",
    )
    linked_vnets: list[AzureIdRef] | None = Field(
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
        default=...,
        title="Virtual Network",
        description="The virtual network to be used for the Private DNS Resolver.",
        examples=[
            "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-name/providers/Microsoft.Network/virtualNetworks/vnet-name",
            "stack://project/stack-name/output-name",
            "stack://project/stack-name/output-name.vnet_id",
        ],
    )
    inbound_endpoint: ResolverInboundEndpoint | None = Field(
        default=None,
        title="Inbound Endpoint",
        description="Inbound endpoint to be used for the Private DNS Resolver.",
    )
    outbound_endpoint: ResolverOutboundEndpoint | None = Field(
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
        opts: pulumi.ResourceOptions | None = None,
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
        self.resolver: dnsresolver.DnsResolver = self._resolver()
        self._outputs()

    def _resolver(self) -> dnsresolver.DnsResolver:
        vnet = AzureResourceId(str(self.config.virtual_network))
        resolver = dnsresolver.DnsResolver(
            resource_name=self.stack.name_for(resource_type=dnsresolver.DnsResolver),
            dns_resolver_name=self.stack.name_for(resource_type=dnsresolver.DnsResolver),
            location=self.stack.location,
            resource_group_name=self.stack.resource_group.name,
            virtual_network=dnsresolver.SubResourceArgs(id=vnet.id),
            opts=self._opts,
        )

        if self.config.inbound_endpoint:
            dnsresolver.InboundEndpoint(
                resource_name=self.stack.name_for(
                    resource_type=dnsresolver.InboundEndpoint,
                ),
                inbound_endpoint_name=self.stack.name_for(
                    resource_type=dnsresolver.InboundEndpoint,
                ),
                dns_resolver_name=resolver.name,
                location=self.stack.location,
                ip_configurations=[
                    dnsresolver.IpConfigurationArgs(
                        private_ip_allocation_method="Static"
                        if self.config.inbound_endpoint.private_ip_address
                        else "Dynamic",
                        subnet=dnsresolver.SubResourceArgs(
                            id=AzureResourceId(str(self.config.inbound_endpoint.subnet_id)).id
                        ),
                        private_ip_address=str(self.config.inbound_endpoint.private_ip_address)
                        if self.config.inbound_endpoint.private_ip_address
                        else None,
                    )
                ],
                resource_group_name=self.stack.resource_group.name,
                opts=self._opts,
            )

        if self.config.outbound_endpoint:
            outboundEndpoint = dnsresolver.OutboundEndpoint(
                resource_name=self.stack.name_for(
                    resource_type=dnsresolver.OutboundEndpoint,
                ),
                outbound_endpoint_name=self.stack.name_for(
                    resource_type=dnsresolver.OutboundEndpoint,
                ),
                dns_resolver_name=resolver.name,
                location=self.stack.location,
                resource_group_name=self.stack.resource_group.name,
                subnet=dnsresolver.SubResourceArgs(
                    id=AzureResourceId(str(self.config.outbound_endpoint.subnet_id)).id
                ),
                opts=self._opts,
            )
            if self.config.outbound_endpoint.rules:
                ruleset = dnsresolver.DnsForwardingRuleset(
                    resource_name=self.stack.name_for(
                        resource_type=dnsresolver.DnsForwardingRuleset,
                    ),
                    dns_forwarding_ruleset_name=self.stack.name_for(
                        resource_type=dnsresolver.DnsForwardingRuleset,
                    ),
                    dns_resolver_outbound_endpoints=[
                        dnsresolver.SubResourceArgs(id=outboundEndpoint.id)
                    ],
                    location=self.stack.location,
                    resource_group_name=self.stack.resource_group.name,
                    opts=self._opts,
                )
                for rule in self.config.outbound_endpoint.rules:
                    targets: list[dnsresolver.TargetDnsServerArgsDict] = [
                        dnsresolver.TargetDnsServerArgsDict({"ip_address": str(ip)})
                        for ip in rule.target_dns_servers
                    ]
                    dnsresolver.ForwardingRule(
                        resource_name=fmt_name(rule.domain_name),
                        forwarding_rule_name=fmt_name(rule.domain_name),
                        resource_group_name=self.stack.resource_group.name,
                        forwarding_rule_state=rule.rule_state,
                        dns_forwarding_ruleset_name=ruleset.name,
                        domain_name=rule.domain_name + ".",
                        target_dns_servers=targets,
                        opts=self._opts,
                    )
                if self.config.outbound_endpoint.linked_vnets:
                    for vnet in self.config.outbound_endpoint.linked_vnets:
                        v = AzureResourceId(str(vnet))
                        dnsresolver.PrivateResolverVirtualNetworkLink(
                            resource_name=f"{v.resource_name}-link",  # type: ignore
                            virtual_network_link_name=f"{v.resource_name}-link",
                            dns_forwarding_ruleset_name=ruleset.name,
                            resource_group_name=self.stack.resource_group.name,
                            virtual_network=dnsresolver.SubResourceArgs(id=v.id),
                            opts=self._opts,
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
                    "inbound_ip": str(self.config.inbound_endpoint.private_ip_address)
                    if self.config.inbound_endpoint
                    else None,
                },
            }
        )

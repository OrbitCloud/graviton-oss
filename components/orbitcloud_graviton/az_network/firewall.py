from ipaddress import IPv4Address, IPv4Network
from typing import Annotated, Any, ClassVar, Literal

import pulumi
from pulumi import ComponentResource
from pulumi_azure_native import insights
from pulumi_azure_native.network.v20230901 import (
    ApplicationRuleArgs,
    AzureFirewall,
    AzureFirewallIPConfigurationArgs,
    AzureFirewallSkuArgs,
    AzureFirewallSkuName,
    AzureFirewallSkuTier,
    DnsSettingsArgs,
    FirewallPolicy,
    FirewallPolicyFilterRuleCollectionActionArgs,
    FirewallPolicyFilterRuleCollectionActionType,
    FirewallPolicyFilterRuleCollectionArgs,
    FirewallPolicyInsightsArgs,
    FirewallPolicyLogAnalyticsResourcesArgs,
    FirewallPolicyLogAnalyticsWorkspaceArgs,
    FirewallPolicyNatRuleCollectionActionArgs,
    FirewallPolicyNatRuleCollectionActionType,
    FirewallPolicyNatRuleCollectionArgs,
    FirewallPolicyRuleApplicationProtocolArgs,
    FirewallPolicyRuleCollectionGroup,
    FirewallPolicyRuleNetworkProtocol,
    FirewallPolicySkuArgs,
    HubIPAddressesArgs,
    HubPublicIPAddressesArgs,
    NetworkRuleArgs,
    SubResourceArgs,
)
from pydantic import BaseModel, ConfigDict, Field, model_validator

from orbitcloud_graviton.az_lib.types import AzureIdRef, StrRef
from orbitcloud_graviton.az_monitor import diagnostic_setting
from orbitcloud_graviton.pulumi_lib import AzureStack

from .helpers import is_fqdn_tag, is_port, is_service_tag
from .public_ip import PublicIp, PublicIpConfig


class NetworkRule(BaseModel):
    name: str
    destination_ip_addresses: StrRef | IPv4Network | str | list[IPv4Network | StrRef] | None = None
    destination_ip_groups: list[AzureIdRef] | None = None
    destination_service_tags: list[str] | None = None
    destination_fqdns: list[str] | None = None
    destination_ports: str | int | list[str | int]
    source_ip_addresses: StrRef | IPv4Network | str | list[IPv4Network | StrRef] | None = None
    source_ip_groups: list[AzureIdRef] | None = None
    protocols: list[Literal["TCP", "UDP", "ICMP"]] | Literal["ANY"] | None = ["TCP"]
    description: str | None = None
    web_categories: list[str] | None = None

    @model_validator(mode="after")
    def validate_network_rule(m: "NetworkRule") -> "NetworkRule":
        # Validate that only one destination type is specified
        destination_fields = [
            "destination_ip_groups",
            "destination_ip_addresses",
            "destination_service_tags",
            "destination_fqdns",
        ]
        destinations = [
            getattr(m, field) for field in destination_fields if getattr(m, field) is not None
        ]
        if len(destinations) != 1:
            raise ValueError(
                "Exactly one of destination_ip_groups, destination_ip_addresses, destination_service_tags, destination_fqdns should be specified."
            )

        # Validate destination addresses
        if m.destination_ip_addresses is not None:
            if isinstance(m.destination_ip_addresses, str):
                try:
                    IPv4Network(m.destination_ip_addresses)
                except ValueError:
                    if m.destination_ip_addresses != "*":
                        raise ValueError(
                            f"Destination address {m.destination_ip_addresses} is not valid."
                        ) from None
            elif isinstance(m.destination_ip_addresses, list):
                for address in m.destination_ip_addresses:
                    if isinstance(address, str):
                        try:
                            IPv4Network(address)
                        except ValueError:
                            if address != "*":
                                raise ValueError(
                                    f"Destination address {address} is not valid."
                                ) from None

        # Validate destination service tags
        if m.destination_service_tags is not None:
            for tag in m.destination_service_tags:
                if not is_service_tag(tag):
                    raise ValueError(f"Service tag {tag} is not valid.")

        # Validate destination FQDNs (example check)
        if m.destination_fqdns is not None:
            for fqdn in m.destination_fqdns:
                if not isinstance(fqdn, str) or len(fqdn) == 0:
                    raise ValueError(f"FQDN {fqdn} is not valid.")
                # TODO: Consider adding sophisticated FQDN validation logic here

        # Validate ports
        if m.destination_ports is not None:
            if isinstance(m.destination_ports, str | int):
                m.destination_ports = [m.destination_ports]

            for item in m.destination_ports:
                is_port(item)

        # Validate source addresses
        if m.source_ip_addresses:
            if isinstance(m.source_ip_addresses, str):
                try:
                    IPv4Network(m.source_ip_addresses)
                except ValueError:
                    if m.source_ip_addresses != "*":
                        raise ValueError(
                            f"Source address {m.source_ip_addresses} is not a valid IP-address/IP-range"
                        ) from None
            elif isinstance(m.source_ip_addresses, list):
                for address in m.source_ip_addresses:
                    if isinstance(address, str):
                        try:
                            IPv4Network(address)
                        except ValueError:
                            if address != "*":
                                raise ValueError(
                                    f"Source address {address} is not a valid IP-address/IP-range"
                                ) from None
        elif not m.source_ip_groups:
            raise ValueError("Source address or group must be specified.")

        return m

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ProtocolPort(BaseModel):
    protocol: Literal["Http", "Https", "Mssql"]
    port: int | None = None

    DEFAULT_PORTS: ClassVar[dict[str, int]] = {
        "Http": 80,
        "Https": 443,
        "Mssql": 1433,
    }

    @model_validator(mode="before")
    def set_default_port(cls, values: Any) -> Any:
        if isinstance(values, dict):
            if values.get("port") is None:
                protocol = values.get("protocol")
                if protocol:
                    values["port"] = cls.DEFAULT_PORTS.get(protocol)
        return values

    @model_validator(mode="after")
    def validate_port(m: "ProtocolPort") -> "ProtocolPort":
        if m.port is None:
            raise ValueError("Port number cannot be None.")
        if m.port < 1 or m.port > 65535:
            raise ValueError(f"Port number {m.port} is out of the valid range (1-65535).")
        return m


class ApplicationRule(BaseModel):
    name: str
    source_ip_addresses: StrRef | IPv4Network | str | list[IPv4Network | StrRef] | None = None
    source_ip_groups: list[AzureIdRef] | None = None
    destination_fqdns: list[str] | None = None
    destination_fqdn_tags: list[str] | None = None
    destination_urls: list[str] | None = None
    destination_web_categories: list[str] | None = None
    protocols: list[ProtocolPort]
    description: str | None = None

    @model_validator(mode="after")
    def validate_network_rule(m: "ApplicationRule") -> "ApplicationRule":
        # Validate that only one destination type is specified
        destination_fields = [
            "destination_fqdns",
            "destination_fqdn_tags",
            "destination_urls",
            "destination_web_categories",
        ]
        destinations = [
            getattr(m, field) for field in destination_fields if getattr(m, field) is not None
        ]
        if len(destinations) != 1:
            raise ValueError(
                "Exactly one of destination_fqdns, destination_fqdn_tags, destination_urls, destination_web_categories should be specified."
            )

        # Validate Destination FQDN tags
        if m.destination_fqdn_tags:
            for tag in m.destination_fqdn_tags:
                if not is_fqdn_tag(tag):
                    raise ValueError(f"FQDN tag {tag} is not valid.")

        # Validate source addresses
        if m.source_ip_addresses:
            if isinstance(m.source_ip_addresses, str):
                try:
                    IPv4Network(m.source_ip_addresses)
                except ValueError:
                    if m.source_ip_addresses != "*":
                        raise ValueError(
                            f"Source address {m.source_ip_addresses} is not a valid IP-address/IP-range"
                        ) from None
        elif not m.source_ip_groups:
            raise ValueError("Source address or group must be specified.")

        return m

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class RuleCollection(BaseModel):
    name: str
    type: Literal["Application", "Network", "DNAT"]
    priority: Annotated[int, Field(ge=100, le=65000)]
    action: Literal["Allow", "Deny"] = "Allow"  # TODO: Consider adding support for DNAT
    rules: list[ApplicationRule | NetworkRule] | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class RuleCollectionGroup(BaseModel):
    name: str
    priority: Annotated[int, Field(ge=100, le=65000)]
    rule_collections: list[RuleCollection]

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class FirewallConfig(BaseModel):
    name: str | None = None
    sku: Literal["Basic", "Standard", "Premium"] = "Basic"
    virtual_hub: AzureIdRef | None = None
    dns_proxy: bool | None = False
    custom_dns_servers: list[IPv4Address] | None = None
    subnet: AzureIdRef
    log_workspace_id: AzureIdRef | None = None
    management_subnet: AzureIdRef | None = None
    rule_collection_groups: list[RuleCollectionGroup] | None = None
    zones: list[Literal["1", "2", "3"]] | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    @model_validator(mode="after")
    def validate_firewall_config(m: "FirewallConfig") -> "FirewallConfig":
        if m.sku == "Basic":
            if not m.management_subnet and not m.virtual_hub:
                raise ValueError("Management subnet is required for Basic SKU")
            if m.dns_proxy:
                raise ValueError("DNS Proxy is not supported for Basic SKU")
            if m.custom_dns_servers:
                raise ValueError("Custom DNS Servers are not supported for Basic SKU")

        # Validate that destination_urls are only used when SKU is Premium
        if m.rule_collection_groups:
            for rcg in m.rule_collection_groups:
                for rc in rcg.rule_collections:
                    if rc.type == "Application" and rc.rules:
                        for rule in rc.rules:
                            if isinstance(rule, ApplicationRule) and rule.destination_urls:
                                if m.sku != "Premium":
                                    raise ValueError(
                                        "destination_urls are only supported if the Firewall SKU is Premium"
                                    )

            # Check for duplicate priorities in Rule Collection Groups
            group_priorities = set()
            for rcg in m.rule_collection_groups:
                if rcg.priority in group_priorities:
                    raise ValueError(
                        f"Duplicate priority {rcg.priority} found in Rule Collection Groups"
                    )
                group_priorities.add(rcg.priority)

                # Check for duplicate priorities in Rule Collections
                collection_priorities = set()
                for rc in rcg.rule_collections:
                    if rc.priority in collection_priorities:
                        raise ValueError(
                            f"Duplicate priority {rc.priority} found in RuleCollections within RuleCollectionGroup {rcg.name}"
                        )
                    collection_priorities.add(rc.priority)

        return m


class Firewall(ComponentResource):
    def __init__(
        self,
        stack: AzureStack,
        config: FirewallConfig,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        self.stack: AzureStack = stack
        self.config: FirewallConfig = config

        super().__init__(
            "Graviton:az_network:AzureFirewall",
            name=f"fw-{stack.workload_name}",
            props=None,
            opts=opts,
        )
        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts1=opts, opts2=pulumi.ResourceOptions(parent=self)
        )

        self.policy: FirewallPolicy = self._firewall_policy()
        self.firewall: AzureFirewall = self._firewall()
        self.diagnostic_settings: insights.DiagnosticSetting | None = self._diagnostic_settings()

        if self.config.rule_collection_groups:
            self._rule_collection_groups(self.config.rule_collection_groups)

    def _firewall(self) -> AzureFirewall:
        return AzureFirewall(
            resource_name=self.stack.name_for(
                resource_type=AzureFirewall,
                workload_name=self.config.name or self.stack.workload_name,
            ),
            azure_firewall_name=self.stack.name_for(
                resource_type=AzureFirewall,
                workload_name=self.config.name or self.stack.workload_name,
            ),
            sku=self._firewall_sku(),
            firewall_policy=SubResourceArgs(id=self.policy.id),
            zones=self._zones(),
            resource_group_name=self.stack.resource_group.name,
            location=self.stack.location,
            ip_configurations=[
                AzureFirewallIPConfigurationArgs(
                    name="ipconfig",
                    public_ip_address=SubResourceArgs(id=self._public_ip()),
                    subnet=SubResourceArgs(id=self.config.subnet),
                )
            ]
            if not self.config.virtual_hub
            else None,
            management_ip_configuration=AzureFirewallIPConfigurationArgs(
                name="management_ipconfig",
                public_ip_address=SubResourceArgs(id=self._public_ip(workload="_management")),
                subnet=SubResourceArgs(id=self.config.management_subnet),
            )
            if self.config.management_subnet
            else None,
            virtual_hub=SubResourceArgs(id=self.config.virtual_hub)
            if self.config.virtual_hub
            else None,
            hub_ip_addresses=HubIPAddressesArgs(
                public_ips=HubPublicIPAddressesArgs(count=2 if self.config.sku == "Basic" else 1)
            )
            if self.config.virtual_hub
            else None,
            opts=pulumi.ResourceOptions(parent=self.policy),
        )

    def _firewall_policy(self) -> FirewallPolicy:
        return FirewallPolicy(
            resource_name=self.stack.name_for(FirewallPolicy),
            firewall_policy_name=self.stack.name_for(FirewallPolicy),
            resource_group_name=self.stack.resource_group.name,
            dns_settings=self._dns_settings(),
            location=self.stack.location,
            insights=self._insights(),
            sku=self._policy_sku(),
        )

    def _dns_settings(self):
        if self.config.custom_dns_servers or self.config.dns_proxy:
            servers = (
                [str(ip) for ip in self.config.custom_dns_servers]
                if self.config.custom_dns_servers
                else None
            )
            return DnsSettingsArgs(
                enable_proxy=self.config.dns_proxy,
                servers=servers,
                require_proxy_for_network_rules=None,  # To-Be-Implemented if needed
            )

    def _insights(self) -> FirewallPolicyInsightsArgs | None:
        if self.config.log_workspace_id:
            return FirewallPolicyInsightsArgs(
                is_enabled=True,
                log_analytics_resources=FirewallPolicyLogAnalyticsResourcesArgs(
                    default_workspace_id=SubResourceArgs(id=self.config.log_workspace_id),
                    workspaces=[
                        FirewallPolicyLogAnalyticsWorkspaceArgs(
                            region=self.stack.location,
                            workspace_id=SubResourceArgs(id=self.config.log_workspace_id),
                        )
                    ],
                ),
            )

    def _public_ip(self, workload: str = ""):
        public_ip_config = PublicIpConfig(
            workload=f"{self.stack.name_for(AzureFirewall)}{workload}",
            address_version="IPv4",
            tier="Regional",
            zone=self._zones(),
        )
        public_ip = PublicIp(
            stack=self.stack, config=public_ip_config, opts=pulumi.ResourceOptions(parent=self)
        )
        return public_ip.public_ip.id

    def _firewall_sku(self):
        tier_mapping = {
            "Basic": AzureFirewallSkuTier.BASIC,
            "Standard": AzureFirewallSkuTier.STANDARD,
            "Premium": AzureFirewallSkuTier.PREMIUM,
        }

        tier = tier_mapping[self.config.sku]

        name = (
            AzureFirewallSkuName.AZF_W_HUB
            if self.config.virtual_hub
            else AzureFirewallSkuName.AZF_W_V_NET
        )

        return AzureFirewallSkuArgs(
            name=name,
            tier=tier,
        )

    def _policy_sku(self):
        tier_mapping = {
            "Basic": AzureFirewallSkuTier.BASIC,
            "Standard": AzureFirewallSkuTier.STANDARD,
            "Premium": AzureFirewallSkuTier.PREMIUM,
        }

        tier = tier_mapping[self.config.sku]

        return FirewallPolicySkuArgs(
            tier=tier,
        )

    def _zones(self):
        return self.config.zones if self.config.zones else None

    def _rule_collection_groups(self, rule_collection_groups: list[RuleCollectionGroup]):
        _parent_dependant = None
        for group in rule_collection_groups:
            policy = FirewallPolicyRuleCollectionGroup(
                resource_name=group.name,
                rule_collection_group_name=group.name,
                firewall_policy_name=self.policy.name,
                resource_group_name=self.stack.resource_group.name,
                priority=group.priority,
                rule_collections=self._rule_collections(group.rule_collections),
                opts=pulumi.ResourceOptions(
                    parent=self.firewall,
                    depends_on=[_parent_dependant] if _parent_dependant else None,
                ),
            )
            _parent_dependant = policy

    def _rule_collections(self, rule_collections: list[RuleCollection]):
        collections = []
        action_map = {
            "Allow": FirewallPolicyFilterRuleCollectionActionType.ALLOW,
            "Deny": FirewallPolicyFilterRuleCollectionActionType.DENY,
            "DNAT": FirewallPolicyNatRuleCollectionActionType.DNAT,
        }

        for collection in rule_collections:
            rules = self._rules(collection.rules) if collection.rules else None

            if collection.type in ["Application", "Network"]:
                collections.append(
                    FirewallPolicyFilterRuleCollectionArgs(
                        name=collection.name,
                        priority=collection.priority,
                        rule_collection_type=collection.type,
                        action=FirewallPolicyFilterRuleCollectionActionArgs(
                            type=action_map[collection.action],
                        ),
                        rules=rules,
                    )
                )
            elif collection.type == "DNAT":
                collections.append(
                    FirewallPolicyNatRuleCollectionArgs(
                        name=collection.name,
                        priority=collection.priority,
                        rule_collection_type=collection.type,
                        action=FirewallPolicyNatRuleCollectionActionArgs(
                            type=action_map[collection.action],
                        ),
                        rules=rules,
                    )
                )

        return collections

    def _rules(
        self, rules: list[NetworkRule | ApplicationRule]
    ) -> list[ApplicationRuleArgs | NetworkRuleArgs] | None:
        if rules:
            constructed_rules = []
            network_protocol_map = {
                "TCP": FirewallPolicyRuleNetworkProtocol.TCP,
                "UDP": FirewallPolicyRuleNetworkProtocol.UDP,
                "ICMP": FirewallPolicyRuleNetworkProtocol.ICMP,
                "ANY": FirewallPolicyRuleNetworkProtocol.ANY,
            }

            for rule in rules:
                if isinstance(rule, NetworkRule):
                    ip_protocols = []
                    if rule.protocols:
                        if isinstance(rule.protocols, str):
                            ip_protocols = [network_protocol_map[rule.protocols]]
                        else:
                            ip_protocols = [network_protocol_map[proto] for proto in rule.protocols]

                    # Convert destination_ports to list of strings
                    if isinstance(rule.destination_ports, str | int):
                        destination_ports = [str(rule.destination_ports)]
                    elif isinstance(rule.destination_ports, list):
                        destination_ports = [str(port) for port in rule.destination_ports]
                    else:
                        destination_ports = None

                    # Create NetworkRuleArgs object
                    rule_args = NetworkRuleArgs(
                        name=rule.name,
                        rule_type="NetworkRule",
                        description=rule.description,
                        ip_protocols=ip_protocols,
                        destination_ports=destination_ports,
                        source_addresses=[str(addr) for addr in rule.source_ip_addresses]
                        if rule.source_ip_addresses
                        else None,
                        source_ip_groups=rule.source_ip_groups if rule.source_ip_groups else None,
                        destination_addresses=[str(addr) for addr in rule.destination_ip_addresses]
                        if rule.destination_ip_addresses
                        else None,
                        destination_ip_groups=rule.destination_ip_groups
                        if rule.destination_ip_groups
                        else None,
                        destination_fqdns=rule.destination_fqdns
                        if rule.destination_fqdns
                        else None,
                    )

                    constructed_rules.append(rule_args)

                elif isinstance(rule, ApplicationRule):
                    protocols = []
                    for protocol in rule.protocols:
                        protocols.append(
                            FirewallPolicyRuleApplicationProtocolArgs(
                                protocol_type=protocol.protocol,
                                port=protocol.port,
                            )
                        )

                    # Create ApplicationRuleArgs object
                    rule_args = ApplicationRuleArgs(
                        name=rule.name,
                        rule_type="ApplicationRule",
                        description=rule.description,
                        protocols=protocols,
                        source_addresses=[str(addr) for addr in rule.source_ip_addresses]
                        if rule.source_ip_addresses
                        else None,
                        source_ip_groups=rule.source_ip_groups if rule.source_ip_groups else None,
                        target_fqdns=rule.destination_fqdns if rule.destination_fqdns else None,
                        target_urls=rule.destination_urls if rule.destination_urls else None,
                        web_categories=rule.destination_web_categories
                        if rule.destination_web_categories
                        else None,
                        fqdn_tags=rule.destination_fqdn_tags
                        if rule.destination_fqdn_tags
                        else None,
                    )

                    constructed_rules.append(rule_args)

            return constructed_rules
        return None

    def _diagnostic_settings(self) -> insights.DiagnosticSetting | None:
        if self.config.log_workspace_id:
            return diagnostic_setting(
                resource=self.firewall,
                log_workspace_id=self.config.log_workspace_id,
                metric_categories=["AllMetrics"],
                log_categories=[
                    "AzureFirewallApplicationRule",
                    "AzureFirewallNetworkRule",
                    "AzureFirewallDnsProxy",
                    "AZFWNetworkRule",
                    "AZFWApplicationRule",
                    "AZFWNatRule",
                    "AZFWThreatIntel",
                    "AZFWIdpsSignature",
                    "AZFWDnsQuery",
                    "AZFWFqdnResolveFailure",
                    "AZFWFatFlow",
                    "AZFWFlowTrace",
                    "AZFWApplicationRuleAggregation",
                    "AZFWNetworkRuleAggregation",
                    "AZFWNatRuleAggregation",
                ],
                opts=pulumi.ResourceOptions(parent=self.firewall),
            )

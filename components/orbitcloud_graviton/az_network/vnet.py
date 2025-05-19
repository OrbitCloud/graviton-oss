from typing import Any

import pulumi
from pulumi import ComponentResource
from pulumi_azure_native import network
from pydantic import BaseModel, ConfigDict, model_validator

from orbitcloud_graviton.az_lib.types import AzureIdRef, AzureResourceId
from orbitcloud_graviton.pulumi_lib import AzureStack, get_provider

from ._enums import NON_NSG_SUBNETS, SPECIAL_SUBNETS, SubnetServiceEndpoints
from .ip_group import IpGroupConfig, ip_group
from .nsg import DEFAULT_DENY_RULE, NsgRuleConfig
from .types import PrivateIPv4Network


class SubnetConfig(BaseModel):
    name: str
    address_prefix: PrivateIPv4Network
    delegation: str | None = None
    private_endpoint_network_policies: network.VirtualNetworkPrivateEndpointNetworkPolicies = (
        network.VirtualNetworkPrivateEndpointNetworkPolicies.ENABLED
    )

    virtual_network_name: str | pulumi.Output[str] | None = None
    service_endpoints: list[SubnetServiceEndpoints] | None = None
    network_rules: list[NsgRuleConfig] | None = None

    @model_validator(mode="after")
    def validate_network_rules(m: "SubnetConfig") -> "SubnetConfig":
        if m.network_rules and m.name in NON_NSG_SUBNETS:
            raise ValueError(f"Subnet {m.name} cannot have network rules")
        return m

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class VnetPeeringConfig(BaseModel):
    allow_forwarded_traffic: bool | None = True
    allow_gateway_transit: bool | None = False
    allow_virtual_network_access: bool | None = True
    use_remote_gateways: bool | None = False
    remote_virtual_network: AzureIdRef

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class VnetConfig(BaseModel):
    address_space: list[PrivateIPv4Network]
    subnets: list[SubnetConfig]
    peered_vnets: list[VnetPeeringConfig] | None = None
    create_default_nsgs: bool | None = False
    create_ip_groups: bool | None = False

    # Validate that subnets are unique, don't overlap and are within the vnet address space
    @model_validator(mode="after")
    def validate_subnets(m: "VnetConfig") -> "VnetConfig":
        subnet_address_prefixes: set[PrivateIPv4Network] = {
            subnet.address_prefix for subnet in m.subnets
        }
        if len(subnet_address_prefixes) != len(m.subnets):
            raise ValueError("Subnet address prefixes must be unique")

        if len(set(m.address_space)) != len(m.address_space):
            raise ValueError("Vnet address space must be unique")

        # Check if subnets are within at least one of the vnet address spaces
        for subnet in m.subnets:
            if not any(
                subnet.address_prefix.subnet_of(other=address_space)
                for address_space in m.address_space
            ):
                raise ValueError(
                    f"Subnet {subnet.name} address prefix {subnet.address_prefix} is not within any of the vnet address spaces"
                )

            # Check if subnet overlaps with any other subnet
            if any(
                subnet.address_prefix.overlaps(other=other_subnet.address_prefix)
                for other_subnet in m.subnets
                if other_subnet != subnet
            ):
                raise ValueError(
                    f"Subnet {subnet.name} address prefix {subnet.address_prefix} overlaps with another subnet"
                )

        return m

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class Vnet(ComponentResource):
    def __init__(
        self,
        stack: AzureStack,
        config: VnetConfig,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        self.stack: AzureStack = stack
        self.config: VnetConfig = config

        super().__init__(
            "Graviton:az_network:Vnet",
            name=f"vnet-{self.stack.workload_name}",
            props=None,
            opts=opts,
        )
        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts1=opts, opts2=pulumi.ResourceOptions(parent=self)
        )

        self.vnet: network.VirtualNetwork = self._vnet()
        self.nsgs: dict[str, network.NetworkSecurityGroup] = self._nsgs()
        self.subnets: dict[str, network.Subnet] = self._subnets()
        self.ip_groups: dict[str, network.IpGroup] | None = self._ip_groups()
        self.vnet_peering = self._vnet_peerings()

        self._outputs()

    def _vnet(self) -> network.VirtualNetwork:
        return network.VirtualNetwork(
            resource_name=self.stack.name_for(network.VirtualNetwork),
            args=network.VirtualNetworkArgs(
                resource_group_name=self.stack.resource_group.name,
                location=self.stack.location,
                address_space=network.AddressSpaceArgs(
                    address_prefixes=[str(x) for x in self.config.address_space],
                ),
            ),
            opts=pulumi.ResourceOptions.merge(
                opts1=self._opts,
                opts2=pulumi.ResourceOptions(
                    ignore_changes=["subnets", "virtual_network_peerings"]
                ),
            ),
        )

    def _nsgs(self) -> dict[str, network.NetworkSecurityGroup]:
        nsgs = {}
        # Declare default deny rule added by default to all NSGs

        for subnet in self.config.subnets:
            if subnet.network_rules or (
                self.config.create_default_nsgs and subnet.name not in NON_NSG_SUBNETS
            ):
                nsg = network.NetworkSecurityGroup(
                    resource_name=f"nsg-{self.stack.name_for(resource_type=network.Subnet, workload_name=subnet.name)}",
                    network_security_group_name=f"nsg-{self.stack.name_for(resource_type=network.Subnet, workload_name=subnet.name)}",
                    resource_group_name=self.stack.resource_group.name,
                    location=self.stack.location,
                    opts=pulumi.ResourceOptions.merge(self._opts, pulumi.ResourceOptions(None)),
                )
                rules = [DEFAULT_DENY_RULE] + (subnet.network_rules or [])
                for i, rule in enumerate(rules):
                    # Handle addresses - single or list -> prefix or prefixes
                    # Handle source addresses
                    if isinstance(rule.source_addresses, list):
                        source_address_prefixes = [str(addr) for addr in rule.source_addresses]
                        source_address_prefix = None
                    else:
                        source_address_prefixes = None
                        source_address_prefix = str(rule.source_addresses)

                    # Handle destination addresses
                    if isinstance(rule.destination_addresses, list):
                        destination_address_prefixes = [
                            str(addr) for addr in rule.destination_addresses
                        ]
                        destination_address_prefix = None
                    else:
                        destination_address_prefixes = None
                        destination_address_prefix = str(rule.destination_addresses)

                    # Set priority automatically if not set
                    if rule.priority is None:
                        rule.priority = 100 + i
                    network.SecurityRule(
                        resource_name=f"nsg-{self.stack.name_for(resource_type=network.Subnet, workload_name=subnet.name)}-{rule.name}-{i}",
                        direction=rule.direction,
                        protocol=rule.protocol,
                        access=rule.action,
                        security_rule_name=rule.name,
                        description=rule.description,
                        destination_port_range=rule.destination_port_range,
                        source_port_range=rule.source_port_range,
                        destination_address_prefix=destination_address_prefix,
                        destination_address_prefixes=destination_address_prefixes,
                        source_address_prefix=source_address_prefix,
                        source_address_prefixes=source_address_prefixes,
                        priority=rule.priority,
                        resource_group_name=self.stack.resource_group.name,
                        network_security_group_name=nsg.name,
                        opts=pulumi.ResourceOptions(parent=nsg),
                    )
                nsgs[subnet.name] = nsg
        return nsgs

    def _subnets(self) -> dict[str, network.Subnet]:
        return {
            subnet.name: network.Subnet(
                resource_name=subnet.name
                if subnet.name in SPECIAL_SUBNETS
                else self.stack.name_for(resource_type=network.Subnet, workload_name=subnet.name),
                args=network.SubnetInitArgs(
                    resource_group_name=self.stack.resource_group.name,
                    virtual_network_name=self.vnet.name,
                    address_prefix=str(subnet.address_prefix),
                    delegations=self._subnet_delegation(subnet),
                    private_endpoint_network_policies=subnet.private_endpoint_network_policies,
                    service_endpoints=self._subnet_service_endpoints_args(subnet),
                    network_security_group=network.NetworkSecurityGroupArgs(
                        id=self.nsgs[subnet.name].id
                    )
                    if self.nsgs.get(subnet.name)
                    else None,
                ),
                opts=pulumi.ResourceOptions(
                    parent=self.vnet,
                ),
            )
            for subnet in self.config.subnets
        }

    def _ip_groups(self) -> dict[str, network.IpGroup] | None:
        if self.config.create_ip_groups:
            ip_groups = {}
            for subnet in self.config.subnets:  # We could maybe use self.subnets instead.
                ip_group_resource = ip_group(
                    stack=self.stack,
                    config=IpGroupConfig(
                        workload=subnet.name
                        if subnet.name in SPECIAL_SUBNETS
                        else self.stack.name_for(
                            resource_type=network.Subnet, workload_name=subnet.name
                        ),
                        ip_addresses=subnet.address_prefix,
                    ),
                    opts=pulumi.ResourceOptions(parent=self.subnets[subnet.name]),
                )
                ip_groups[subnet.name] = ip_group_resource
            return ip_groups
        return None

    def _subnet_service_endpoints_args(
        self, subnet: SubnetConfig
    ) -> list[network.ServiceEndpointPropertiesFormatArgs] | None:
        return (
            [
                network.ServiceEndpointPropertiesFormatArgs(
                    service=service,
                )
                for service in subnet.service_endpoints
            ]
            if subnet.service_endpoints
            else None
        )

    def _subnet_delegation(self, subnet: SubnetConfig) -> list[network.DelegationArgs] | None:
        return (
            [
                (
                    network.DelegationArgs(
                        name=f"delegation-{subnet.name}-{subnet.delegation}",
                        service_name=subnet.delegation,
                    )
                )
            ]
            if subnet.delegation
            else None
        )

    def _vnet_peerings(self) -> None:
        if self.config.peered_vnets:
            for peering in self.config.peered_vnets:
                target_vnet = AzureResourceId(str(peering.remote_virtual_network))
                provider = get_provider(str(target_vnet.subscription_id))
                vnet_name = self.stack.name_for(network.VirtualNetwork)
                # Peer source VNET to target VNET
                network.VirtualNetworkPeering(
                    resource_name=f"{vnet_name}-to-{target_vnet.resource_name}_peering",
                    resource_group_name=self.stack.resource_group.name,
                    virtual_network_name=self.vnet.name,
                    remote_virtual_network=network.SubResourceArgs(id=target_vnet.id),
                    allow_forwarded_traffic=peering.allow_forwarded_traffic,
                    allow_gateway_transit=peering.allow_gateway_transit,
                    allow_virtual_network_access=peering.allow_virtual_network_access,
                    use_remote_gateways=peering.use_remote_gateways,
                    opts=pulumi.ResourceOptions(
                        parent=self.vnet,
                    ),
                )

                # Peer target VNET to source VNET
                network.VirtualNetworkPeering(
                    resource_name=f"{target_vnet.resource_name}-to-{vnet_name}_peering",
                    resource_group_name=target_vnet.resource_group_name,
                    virtual_network_name=target_vnet.resource_name,
                    remote_virtual_network=network.SubResourceArgs(id=self.vnet.id),
                    allow_forwarded_traffic=peering.allow_forwarded_traffic,
                    allow_gateway_transit=peering.allow_gateway_transit,
                    allow_virtual_network_access=peering.allow_virtual_network_access,
                    use_remote_gateways=peering.use_remote_gateways,
                    opts=pulumi.ResourceOptions(parent=self.vnet, provider=provider),
                )

    def _outputs(self) -> None:
        self.register_outputs(
            outputs={"vnet": self.vnet, "subnets": self.subnets, "ip_groups": self.ip_groups}
        )

        def _subnet_export() -> dict:
            subnet_export: dict[str, Any] = {}
            for name, subnet in self.subnets.items():
                subnet_export[name] = {
                    "name": subnet.name.apply(lambda x: x),
                    "id": subnet.id.apply(lambda x: x),
                    "address_prefix": subnet.address_prefix.apply(lambda x: x),
                }
            return subnet_export

        # TODO: Should we rather export this under _subnet_export? > ip_group_id, ip_group_name
        def _ipgroup_export() -> dict | None:
            if self.ip_groups:
                ip_group_export: dict[str, Any] = {}
                for name, ip_group in self.ip_groups.items():
                    ip_group_export[name] = {
                        "name": ip_group.name.apply(lambda x: x),
                        "id": ip_group.id.apply(lambda x: x),
                        "ip_addresses": ip_group.ip_addresses.apply(lambda x: x),
                    }
                return ip_group_export

        self.stack.export(
            exports={
                "vnet": {
                    "id": self.vnet.id,
                    "name": self.vnet.name,
                },
                "subnets": _subnet_export(),
                "ip_groups": _ipgroup_export(),
            }
        )

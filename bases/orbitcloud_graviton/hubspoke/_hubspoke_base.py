from typing import Any

import pulumi
from pulumi_azure_native import resources

from orbitcloud_graviton.az_network import (
    DnsZone,
    DnsZoneConfig,
    PrivateDnsResolver,
    PrivateDnsResolverConfig,
    PrivateDnsZone,
    PrivateDNSZoneConfig,
    VirtualNetworkGateway,
    VirtualNetworkGatewayConfig,
    VirtualWan,
    VirtualWanConfig,
    Vnet,
    VnetConfig,
    VwanP2sVpnGw,
    VwanP2sVpnGwConfig,
    VwanS2sVpnGatewayConfig,
    VwanS2SVpnGw,
)
from orbitcloud_graviton.pulumi_lib import AzureStack, PulumiConfig, get_azure_stack
from orbitcloud_graviton.pulumi_lib.helpers import fmt_name
from orbitcloud_graviton.pulumi_lib.stack_schema import generate_stack_schema
from orbitcloud_graviton.pulumi_lib.types import DomainName

from .privateendpoint_zones import default_private_endpoint_zones


class NetworkBaseConfig(PulumiConfig):
    vnet: VnetConfig
    vwan: VirtualWanConfig | None = None
    p2s_vpn: VwanP2sVpnGwConfig | None = None
    s2s_vpn: VwanS2sVpnGatewayConfig | None = None
    dns_zone: DnsZoneConfig | None = None
    dns_zones: list[DnsZoneConfig] | None = None
    private_dns_zones: list[PrivateDNSZoneConfig] | None = None
    private_dns_resolver: PrivateDnsResolverConfig | None = None
    vpn: VirtualNetworkGatewayConfig | None = None


def deploy_hub_spoke():
    generate_stack_schema(model=NetworkBaseConfig, output_file=".stack_schema.json")
    config: NetworkBaseConfig = NetworkBaseConfig.model_validate({})

    stack: AzureStack = get_azure_stack()
    rg: resources.ResourceGroup = stack.resource_group

    ##########################################
    # Virtual Network
    ##########################################
    Vnet(
        stack=stack,
        config=config.vnet,
        opts=pulumi.ResourceOptions(parent=rg),
    )

    ##########################################
    # Virtual WAN, HUB and VPN
    ##########################################
    if config.vwan:
        vwan = VirtualWan(
            stack=stack,
            config=config.vwan,
            opts=pulumi.ResourceOptions(parent=rg),
        )

        if config.p2s_vpn:
            VwanP2sVpnGw(
                stack=stack,
                config=config.p2s_vpn,
                vhub=vwan.vhub,
                opts=pulumi.ResourceOptions(parent=vwan.vwan),
            )

        if config.s2s_vpn:
            VwanS2SVpnGw(
                stack=stack,
                config=config.s2s_vpn,
                vhub=vwan.vhub,
                vwan=vwan.vwan,
                opts=pulumi.ResourceOptions(parent=vwan.vwan),
            )

        private_endpoint_dns_zones: dict[DomainName, dict[str, Any]] = {}
        for zone_name in default_private_endpoint_zones():
            if zone_name in private_endpoint_dns_zones:
                continue

            _pdns_zone = PrivateDnsZone(
                stack=stack.model_copy(update={"skip_exports": True}),
                config=PrivateDNSZoneConfig(
                    name=zone_name,
                    linked_vnets=[
                        spoke.remote_vnet_id
                        for spoke in list(config.vwan.hub_vnet_connections or [])
                    ],
                ),
                opts=pulumi.ResourceOptions(parent=rg),
            )
            private_endpoint_dns_zones[zone_name] = {
                "id": _pdns_zone.zone.id,
            }

        stack.export(
            exports={
                "private_endpoint_dns_zones": private_endpoint_dns_zones,
            }
        )

    ##########################################
    # VPN Gateway (S2S and/or P2S, non-VWAN)
    ##########################################

    if config.vpn:
        VirtualNetworkGateway(
            stack=stack,
            config=config.vpn,
            opts=pulumi.ResourceOptions(parent=rg),
        )

    ##########################################
    # DNS Zones
    ##########################################
    dns_zones: dict[str, DnsZone] = {}
    if config.dns_zone:
        dns_zones[config.dns_zone.name] = DnsZone(
            stack=stack,
            config=config.dns_zone.model_copy(update={"skip_exports": True}),
            opts=pulumi.ResourceOptions(parent=rg),
        )

    if config.dns_zones:
        for zone in config.dns_zones:
            dns_zones[zone.name] = DnsZone(
                stack=stack,
                config=zone.model_copy(update={"skip_exports": True}),
                opts=pulumi.ResourceOptions(parent=rg),
            )

    stack.export(
        exports={
            "dns_zones": {
                fmt_name(v=zone_name): {
                    "id": zone.zone.id,
                }
                for zone_name, zone in dns_zones.items()
            }
        }
    )

    ##########################################
    # Private DNS Resolver
    ##########################################
    if config.private_dns_resolver:
        PrivateDnsResolver(
            stack=stack,
            config=config.private_dns_resolver,
            opts=pulumi.ResourceOptions(parent=rg),
        )

    ##########################################
    # Private DNS Zones
    ##########################################
    if config.private_dns_zones:
        private_zones: dict[str, PrivateDnsZone] = {}
        for zone in config.private_dns_zones:
            private_zones[zone.name] = PrivateDnsZone(
                stack=stack.model_copy(update={"skip_exports": True}),
                config=zone,
                opts=pulumi.ResourceOptions(parent=rg),
            )
        stack.export(
            exports={
                "private_dns_zones": {
                    fmt_name(v=zone_name): {
                        "id": zone.zone.id,
                    }
                    for zone_name, zone in private_zones.items()
                }
            }
        )

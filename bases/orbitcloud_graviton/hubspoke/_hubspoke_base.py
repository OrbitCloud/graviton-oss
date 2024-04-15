from typing import Any, Dict, List, Optional

import pulumi
from pulumi_azure_native import resources

from orbitcloud_graviton.az_network import (
    DnsZone,
    DnsZoneConfig,
    P2sVpnGw,
    P2sVpnGwConfig,
    PrivateDnsResolver,
    PrivateDnsResolverConfig,
    PrivateDnsZone,
    PrivateDNSZoneConfig,
    VirtualWan,
    VirtualWanConfig,
    Vnet,
    VnetConfig,
)
from orbitcloud_graviton.pulumi_lib import AzureStack, PulumiConfig, get_azure_stack
from orbitcloud_graviton.pulumi_lib.stack_schema import generate_stack_schema
from orbitcloud_graviton.pulumi_lib.types import DomainName

from .privateendpoint_zones import default_private_endpoint_zones


class NetworkBaseConfig(PulumiConfig):
    vnet: VnetConfig
    vwan: Optional[VirtualWanConfig] = None
    p2s_vpn: Optional[P2sVpnGwConfig] = None
    dns_zone: Optional[DnsZoneConfig] = None
    private_dns_zones: Optional[List[PrivateDNSZoneConfig]] = None
    private_dns_resolver: Optional[PrivateDnsResolverConfig] = None


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
    # Virtual WAN, HUB and P2S VPN
    ##########################################
    if config.vwan:
        vwan = VirtualWan(
            stack=stack,
            config=config.vwan,
            opts=pulumi.ResourceOptions(parent=rg),
        )

        if config.p2s_vpn:
            P2sVpnGw(
                stack=stack,
                config=config.p2s_vpn,
                vhub=vwan.vhub,
                opts=pulumi.ResourceOptions(parent=vwan.vwan),
            )

        private_endpoint_dns_zones: Dict[DomainName, Dict[str, Any]] = {}
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
    # DNS Zones
    ##########################################
    if config.dns_zone:
        DnsZone(
            stack=stack,
            config=config.dns_zone,
            opts=pulumi.ResourceOptions(parent=rg),
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
        for zone in config.private_dns_zones:
            PrivateDnsZone(
                stack=stack.model_copy(update={"exports_prefix": zone.name}),
                config=zone,
                opts=pulumi.ResourceOptions(parent=rg),
            )

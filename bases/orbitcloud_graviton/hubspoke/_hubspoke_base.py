from typing import List, Optional

import pulumi
from pulumi_azure_native import resources

from orbitcloud_graviton.az_network import (
    DnsZone,
    DnsZoneConfig,
    P2sVpnGw,
    P2sVpnGwConfig,
    PrivateDnsZone,
    PrivateDNSZoneConfig,
    VirtualWan,
    VirtualWanConfig,
    Vnet,
    VnetConfig,
)
from orbitcloud_graviton.pulumi_lib import AzureBase, PulumiConfig, get_azure_stack
from orbitcloud_graviton.pulumi_lib.stack_schema import generate_stack_schema


class NetworkBaseConfig(PulumiConfig):
    vnet: VnetConfig
    vwan: Optional[VirtualWanConfig] = None
    p2s_vpn: Optional[P2sVpnGwConfig] = None
    dns_zone: Optional[DnsZoneConfig] = None
    private_dns_zones: Optional[List[PrivateDNSZoneConfig]] = None


def deploy_hub_spoke():
    generate_stack_schema(model=NetworkBaseConfig, output_file=".stack_schema.json")
    config: NetworkBaseConfig = NetworkBaseConfig.model_validate({})

    stack: AzureBase = get_azure_stack()
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
    # Private DNS Zones
    ##########################################
    if config.private_dns_zones:
        for zone in config.private_dns_zones:
            PrivateDnsZone(
                stack=stack.model_copy(update={"exports_prefix": zone.name}),
                config=zone,
                opts=pulumi.ResourceOptions(parent=rg),
            )

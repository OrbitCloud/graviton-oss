from typing import Optional

import pulumi

from orbitcloud_graviton.az_network import P2sVpnGw, P2sVpnGwConfig, VirtualWan, VirtualWanConfig, Vnet, VnetConfig
from orbitcloud_graviton.pulumi_lib import PulumiConfig, get_azure_stack


class NetworkBaseConfig(PulumiConfig):
    vnet: VnetConfig
    vwan: Optional[VirtualWanConfig] = None
    p2s_vpn: Optional[P2sVpnGwConfig] = None


def deploy_hub_spoke():
    config = NetworkBaseConfig.model_validate({})

    # Get Azure Stack and export resource group
    stack = get_azure_stack()
    pulumi.export("resource_group_id", stack.resource_group.id)
    pulumi.export("resource_group_name", stack.resource_group.name)

    # Create vnet and subnets
    vnet = Vnet(config.vnet)
    pulumi.export("vnet_id", vnet.vnet.id)
    pulumi.export(
        "subnets",
        vnet.vnet.subnets.apply(
            lambda args: {
                f"{subnet.name}": {
                    "name": subnet.name,
                    "id": subnet.id,
                    "address_prefix": subnet.address_prefix,
                }
                for subnet in args
            }
        ),
    )

    # If virtual wan / hub is enabled, create it
    if config.vwan:
        vwan = VirtualWan(config.vwan)
        pulumi.export("vwan_id", vwan.vwan.id)
        pulumi.export("vhub_id", vwan.vhub.id)

        # If P2S VPN is enabled, create it
        if config.p2s_vpn:
            p2s_vpngw = P2sVpnGw(config.p2s_vpn, vwan.vhub)
            pulumi.export("p2s_vpngw_id", p2s_vpngw.p2s_vpngw.id)

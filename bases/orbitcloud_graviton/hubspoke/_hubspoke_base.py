from typing import Optional

from orbitcloud_graviton.az_network import (
    P2sVpnGw,
    P2sVpnGwConfig,
    VirtualWan,
    VirtualWanConfig,
    Vnet,
    VnetConfig,
)
from orbitcloud_graviton.pulumi_lib import AzureBase, PulumiConfig, get_azure_stack


class NetworkBaseConfig(PulumiConfig):
    vnet: VnetConfig
    vwan: Optional[VirtualWanConfig] = None
    p2s_vpn: Optional[P2sVpnGwConfig] = None


def deploy_hub_spoke():
    config: NetworkBaseConfig = NetworkBaseConfig.model_validate({})

    stack: AzureBase = get_azure_stack()

    vnet = Vnet(
        stack=stack,
        config=config.vnet,
    )

    if config.vwan:
        vwan = VirtualWan(
            stack=stack,
            config=config.vwan,
        )
        vnet.vhub_connection(vwan.vhub)

        if config.p2s_vpn:
            P2sVpnGw(
                stack=stack,
                config=config.p2s_vpn,
                vhub=vwan.vhub,
            )

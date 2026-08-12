import pulumi

from orbitcloud_graviton.az_network import VnetConfig
from orbitcloud_graviton.az_network.vnet import Vnet
from orbitcloud_graviton.pulumi_lib import AzureStack
from orbitcloud_graviton.pulumi_mocks import set_mocks

set_mocks()

HUB_VNET_ID = (
    "/subscriptions/11111111-1111-1111-1111-111111111111"
    "/resourceGroups/rg-hub/providers/Microsoft.Network/virtualNetworks/vnet-hub"
)


@pulumi.runtime.test
def test_spoke_to_hub_peering_gateway_flags_are_mirrored(stack: AzureStack) -> None:
    """A spoke that borrows the hub's gateway must not offer gateway transit,
    and the reverse (hub-side) peering must get the opposite flags — otherwise
    the hub, which owns the gateway, would illegally be told to use a remote one.
    """
    config = VnetConfig.model_validate(
        {
            "address_space": ["10.10.0.0/16"],
            "subnets": [{"name": "workload", "address_prefix": "10.10.1.0/24"}],
            "peered_vnets": [
                {
                    "remote_virtual_network": HUB_VNET_ID,
                    "allow_gateway_transit": False,
                    "use_remote_gateways": True,
                }
            ],
        }
    )

    vnet = Vnet(stack=stack, config=config)
    peerings = vnet.vnet_peering

    assert len(peerings) == 2
    spoke_to_hub, hub_to_spoke = peerings

    def check(args) -> None:
        (
            spoke_agt,
            spoke_urg,
            hub_agt,
            hub_urg,
        ) = args

        # Spoke side: no gateway to share, borrows the hub's gateway.
        assert spoke_agt is False
        assert spoke_urg is True

        # Hub side: owns and shares the gateway, does not borrow one.
        assert hub_agt is True
        assert hub_urg is False

    pulumi.Output.all(
        spoke_to_hub.allow_gateway_transit,
        spoke_to_hub.use_remote_gateways,
        hub_to_spoke.allow_gateway_transit,
        hub_to_spoke.use_remote_gateways,
    ).apply(check)


@pulumi.runtime.test
def test_explicit_remote_flags_override_the_mirror(stack: AzureStack) -> None:
    """Explicit remote_* flags take precedence over the mirrored defaults."""
    config = VnetConfig.model_validate(
        {
            "address_space": ["10.20.0.0/16"],
            "subnets": [{"name": "workload", "address_prefix": "10.20.1.0/24"}],
            "peered_vnets": [
                {
                    "remote_virtual_network": HUB_VNET_ID,
                    "allow_gateway_transit": False,
                    "use_remote_gateways": True,
                    # Override: do not let the peer share a gateway back.
                    "remote_allow_gateway_transit": False,
                    "remote_use_remote_gateways": False,
                }
            ],
        }
    )

    vnet = Vnet(stack=stack, config=config)
    _spoke_to_hub, hub_to_spoke = vnet.vnet_peering

    def check(args) -> None:
        hub_agt, hub_urg = args
        assert hub_agt is False
        assert hub_urg is False

    pulumi.Output.all(
        hub_to_spoke.allow_gateway_transit,
        hub_to_spoke.use_remote_gateways,
    ).apply(check)

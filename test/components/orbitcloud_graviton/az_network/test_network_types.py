from ipaddress import IPv4Network

import pytest
from pydantic import BaseModel

from orbitcloud_graviton.az_network.types import PrivateIPv4Network, PublicIPv4Network


class DemoModel(BaseModel):
    public_network: PublicIPv4Network | None = None
    private_network: PrivateIPv4Network | None = None


def test_public_ipv4_network_validation() -> None:
    model = DemoModel.model_validate({"public_network": "8.8.8.0/24"})

    assert isinstance(model.public_network, IPv4Network)
    assert model.public_network == IPv4Network("8.8.8.0/24")


def test_public_network_without_netmask_exception() -> None:
    with pytest.raises(ValueError):
        DemoModel.model_validate({"public_network": "8.8.8.0"})


def test_public_network_private_cidr_exception() -> None:
    with pytest.raises(ValueError):
        DemoModel.model_validate({"public_network": "10.0.0.0/16"})


def test_private_network_validation() -> None:
    model = DemoModel.model_validate({"private_network": "10.0.0.0/16"})
    assert isinstance(model.private_network, IPv4Network)
    assert model.private_network == IPv4Network("10.0.0.0/16")


def test_private_network_without_netmask_exception() -> None:
    with pytest.raises(ValueError):
        DemoModel.model_validate({"private_network": "10.0.0.0"})


def test_private_network_public_cidr_exception() -> None:
    with pytest.raises(ValueError):
        DemoModel.model_validate({"private_network": "8.8.8.0/24"})

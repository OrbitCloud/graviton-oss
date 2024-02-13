from ipaddress import IPv4Network
from typing import Optional

import pytest
from pydantic import BaseModel

from orbitcloud_graviton.az_network.types import PrivateIPv4Network, PublicIPv4Network


class DemoModel(BaseModel):
    public_network: Optional[PublicIPv4Network] = None
    private_network: Optional[PrivateIPv4Network] = None


def test_public_ipv4_network() -> None:
    model = DemoModel.model_validate({"public_network": "8.8.8.0/24"})

    assert isinstance(model.public_network, IPv4Network)
    assert model.public_network == IPv4Network("8.8.8.0/24")

    with pytest.raises(ValueError):
        DemoModel.model_validate({"public_network": "8.8.8.0"})

    with pytest.raises(ValueError):
        DemoModel.model_validate({"public_network": "10.0.0.0/16"})


def test_private_ipv4_network() -> None:
    model = DemoModel.model_validate({"private_network": "10.0.0.0/16"})

    assert isinstance(model.private_network, IPv4Network)
    assert model.private_network == IPv4Network("10.0.0.0/16")

    with pytest.raises(ValueError):
        DemoModel.model_validate({"private_network": "10.0.0.0"})

    with pytest.raises(ValueError):
        DemoModel.model_validate({"private_network": "8.8.8.0/24"})

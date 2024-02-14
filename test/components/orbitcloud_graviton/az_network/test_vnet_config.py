from ipaddress import IPv4Network

import pytest

from orbitcloud_graviton.az_network import VnetConfig


@pytest.fixture
def test_vnet_config_validation():
    config: VnetConfig = VnetConfig.model_validate(
        {
            "address_space": ["10.0.0.0/16"],
            "subnets": [
                {"name": "subnet1", "address_prefix": "10.0.1.0/24"},
                {"name": "subnet2", "address_prefix": "10.0.2.0/24"},
            ],
        }
    )
    assert isinstance(config, VnetConfig)
    assert isinstance(config.address_space[0], IPv4Network)
    assert config.address_space[0] == IPv4Network(address="10.0.0.0/16")
    assert isinstance(config.subnets, list)
    assert isinstance(config.subnets[0].address_prefix, IPv4Network)
    assert config.subnets[0].address_prefix == IPv4Network(address="10.0.1.0/24")
    assert config.subnets[0].name == "subnet1"


def test_bad_vnet_config_public_address_space() -> None:
    with pytest.raises(ValueError):
        VnetConfig.model_validate(
            {
                "address_space": ["8.8.8.8/16"],
            }
        )


def test_vnet_missing_netmask_exception() -> None:
    with pytest.raises(ValueError):
        VnetConfig.model_validate(
            {
                "address_space": ["10.0.0.0"],
            }
        )


def test_vnet_subnet_not_within_address_space() -> None:
    with pytest.raises(ValueError):
        VnetConfig.model_validate(
            {
                "address_space": ["10.0.0.0/16"],
                "subnets": [
                    {"name": "subnet1", "address_prefix": "192.168.1.0/24"},
                ],
            }
        )


def test_vnet_subnet_without_netmask_exception() -> None:
    with pytest.raises(ValueError):
        VnetConfig.model_validate(
            {
                "address_space": ["10.0.0.0/16"],
                "subnets": [
                    {"name": "subnet1", "address_prefix": "192.168.1.0"},
                ],
            }
        )


def test_vnet_unique_subnets_exception() -> None:
    with pytest.raises(ValueError):
        VnetConfig.model_validate(
            {
                "address_space": ["10.0.0.0/16"],
                "subnets": [
                    {"name": "subnet1", "address_prefix": "10.0.1.0/24"},
                    {"name": "subnet2", "address_prefix": "10.0.1.0/24"},
                ],
            }
        )


def test_vnet_overlapping_subnets() -> None:
    with pytest.raises(ValueError) as e:
        VnetConfig.model_validate(
            {
                "address_space": ["10.0.0.0/16"],
                "subnets": [
                    {"name": "subnet1", "address_prefix": "10.0.1.0/24"},
                    {"name": "subnet2", "address_prefix": "10.0.1.0/25"},
                ],
            }
        )
        assert "overlaps with another subnet" in str(e)

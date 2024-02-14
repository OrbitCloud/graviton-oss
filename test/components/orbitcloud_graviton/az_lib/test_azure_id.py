from uuid import UUID

import pytest
from pydantic import TypeAdapter

from orbitcloud_graviton.az_lib import AzureResourceId


@pytest.fixture
def azure_resource_id() -> AzureResourceId:
    return AzureResourceId(
        "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.Network/virtualNetworks/vnet"
    )


@pytest.fixture
def azure_sub_resource_id() -> AzureResourceId:
    return AzureResourceId(
        "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.Network/virtualNetworks/vnet/subnets/subnet1"
    )


def test_azure_resource_id_invalid():
    with pytest.raises(ValueError):
        AzureResourceId("invalid")


def test_azure_resource_id_validation(azure_resource_id: AzureResourceId):
    assert AzureResourceId.is_valid(azure_resource_id.id)


def test_azure_resource_id_validation_error():
    ta = TypeAdapter(AzureResourceId)
    with pytest.raises(ValueError):
        AzureResourceId("invalid")
    with pytest.raises(ValueError):
        ta.validate_python("invalid")


def test_azure_resource_id_params(azure_resource_id: AzureResourceId):
    assert azure_resource_id.subscription_id == UUID("00000000-0000-0000-0000-000000000000")
    assert azure_resource_id.resource_group_name == "rg"
    assert azure_resource_id.provider == "Microsoft.Network"
    assert azure_resource_id.resource_type == "virtualNetworks"
    assert azure_resource_id.resource_name == "vnet"
    assert azure_resource_id.sub_resource is None


def test_azure_sub_resource_id_params(azure_sub_resource_id: AzureResourceId):
    assert azure_sub_resource_id.subscription_id == UUID("00000000-0000-0000-0000-000000000000")
    assert azure_sub_resource_id.resource_group_name == "rg"
    assert azure_sub_resource_id.provider == "Microsoft.Network"
    assert azure_sub_resource_id.resource_type == "virtualNetworks"
    assert azure_sub_resource_id.resource_name == "vnet"
    assert azure_sub_resource_id.sub_resource == "subnets/subnet1"


def test_azure_resource_id_comparison(azure_resource_id: AzureResourceId):
    assert azure_resource_id == azure_resource_id.id
    assert str(azure_resource_id) == azure_resource_id.id
    assert str(azure_resource_id) == azure_resource_id

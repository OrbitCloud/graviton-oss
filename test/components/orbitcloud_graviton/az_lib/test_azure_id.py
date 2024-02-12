from uuid import UUID

import pytest
from pydantic import TypeAdapter

from orbitcloud_graviton.pulumi_mocks import set_mocks

set_mocks()

from orbitcloud_graviton.az_lib import AzureResourceId  # noqa
from orbitcloud_graviton.az_lib.types import parse_stack_reference  # noqa


def test_azure_resource_id():
    ta = TypeAdapter(AzureResourceId)

    id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.Network/virtualNetworks/vnet"
    assert AzureResourceId.is_valid(id)
    assert AzureResourceId.is_valid("invalid") is False
    resource_id = AzureResourceId(id)
    assert resource_id == id
    assert resource_id.id == id
    assert str(resource_id) == id
    assert ta.validate_python(id) == resource_id

    with pytest.raises(ValueError):
        AzureResourceId("invalid")
    with pytest.raises(ValueError):
        ta.validate_python("invalid")

    assert resource_id.subscription_id == UUID("00000000-0000-0000-0000-000000000000")
    assert resource_id.resource_group_name == "rg"
    assert resource_id.provider == "Microsoft.Network"
    assert resource_id.resource_type == "virtualNetworks"
    assert resource_id.resource_name == "vnet"
    assert resource_id.sub_resource is None

    id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.Network/virtualNetworks/vnet/subnets/subnet1"
    resource_id = AzureResourceId(id)
    assert resource_id.subscription_id == UUID("00000000-0000-0000-0000-000000000000")
    assert resource_id.resource_group_name == "rg"
    assert resource_id.provider == "Microsoft.Network"
    assert resource_id.resource_type == "virtualNetworks"
    assert resource_id.resource_name == "vnet"
    assert resource_id.sub_resource == "subnets/subnet1"


def test_parse_stack_reference():
    with pytest.raises(ValueError):
        parse_stack_reference("stack://too_few/parts")

    with pytest.raises(ValueError):
        parse_stack_reference("stack://too/many/parts/here/now")

    assert parse_stack_reference("stack://org/project/stack/output") == (
        "org/project/stack",
        "output",
    )
    assert parse_stack_reference("stack://project/stack/output") == (
        "mock-org/project/stack",
        "output",
    )

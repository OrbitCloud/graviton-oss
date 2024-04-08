import pulumi
import pytest

from orbitcloud_graviton.az_network import PrivateEndpointConfig
from orbitcloud_graviton.pulumi_mocks import set_mocks


# Define the MockResource class
class MockResource:
    def __init__(self, id, name, location, _name):
        self.id = id
        self.name = name
        self.location = location
        self._name = _name


@pytest.fixture(scope="module", autouse=True)
def pulumi_projects_mock():
    set_mocks(
        {
            "azure-native:location": "northeurope",
            "mock-project:workload_name": "privateendpoint",
            "mock-project:env": "dev",
        }
    )

    config = pulumi.Config()

    return {
        "location": pulumi.Config("azure-native").require("location"),
        "workload_name": config.require("workload_name"),
        "env": config.require("env"),
        "tags": {"tag1": "value1", "tag2": "value2"},
    }


@pytest.fixture
def private_endpoint_config():
    uuid_mock = "00000000-0000-0000-0000-000000000000"
    return PrivateEndpointConfig(
        subnet_id=f"/subscriptions/{uuid_mock}/resourceGroups/rg_name/providers/Microsoft.Network/virtualNetworks/vnet_name/subnets/subnet_name",
        private_dns_zone_id=f"/subscriptions/{uuid_mock}/resourceGroups/rg_name/providers/Microsoft.Network/privateDnsZones/private_dns_zone_name",
    )


@pytest.fixture
def mock_resource(pulumi_projects_mock):
    # Use the location from the pulumi_projects_mock fixture
    location = pulumi_projects_mock["location"]
    resource_name = "resource_name_string"
    return MockResource(
        id="resource_id_string",
        name=resource_name,
        location=location,
        _name=resource_name,
    )


# @pulumi.runtime.test
# def test_az_private_endpoint(stack, private_endpoint_config, mock_resource):
#     private_endpoint = PrivateEndpoint(
#         target_resource=mock_resource,
#         stack=stack,
#         config=private_endpoint_config,
#     )

#     assert isinstance(private_endpoint, network.PrivateEndpoint)

#     def check_parameters(args):
#         privateendpoint_location, privateendpoint_tags = args

#         # Check that the location is correct
#         assert privateendpoint_location == stack.location, "Private endpoint location mismatch"

#         # Check that all the tags are set correctly
#         assert privateendpoint_tags == stack.tags, "Private endpoint tags mismatch"

#         # Check the private endpoint name prefix
#         assert private_endpoint._name.startswith("pep-"), "Private endpoint name mismatch"

#     return pulumi.Output.all(
#         private_endpoint.location,
#         private_endpoint.tags,
#     ).apply(check_parameters)

import pulumi
import pytest
from pulumi_azure_native.network import v20230201 as network

from orbitcloud_graviton.az_network import PrivateEndpointConfig, az_private_endpoint
from orbitcloud_graviton.az_resources import az_resource_group
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
    # Mock the PrivateEndpointConfig with necessary details
    return PrivateEndpointConfig(
        target_resource_type="Microsoft.Sql/servers",
        subnet="subnet_id_string",
        private_dns_zone_id="dns_zone_id_string",
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


@pulumi.runtime.test
def test_az_private_endpoint(pulumi_projects_mock, private_endpoint_config, mock_resource):
    workload_name, env, location, tags = (
        pulumi_projects_mock["workload_name"],
        pulumi_projects_mock["env"],
        pulumi_projects_mock["location"],
        pulumi_projects_mock["tags"],
    )

    resource_group = az_resource_group(workload_name=workload_name, env=env, location=location, tags=tags)

    private_endpoint = az_private_endpoint(
        resource=mock_resource,
        resource_group=resource_group,
        private_endpoint_config=private_endpoint_config,
        tags=tags,
    )

    assert isinstance(private_endpoint, network.PrivateEndpoint)

    def check_parameters(args):
        privateendpoint_location, privateendpoint_tags = args

        # Check that the location is correct
        assert privateendpoint_location == location, "Private endpoint location mismatch"

        # Check that all the tags are set correctly
        assert privateendpoint_tags == tags, "Private endpoint tags mismatch"

        # Check the private endpoint name prefix
        assert private_endpoint._name.startswith("pep-"), "Private endpoint name mismatch"

    return pulumi.Output.all(
        private_endpoint.location,
        private_endpoint.tags,
    ).apply(check_parameters)

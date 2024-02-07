import pulumi
import pytest

from orbitcloud_graviton.az_resources import az_resource_group
from orbitcloud_graviton.pulumi_mocks import set_mocks


@pytest.fixture(scope="module", autouse=True)
def pulumi_project_mock():
    set_mocks(
        {
            "azure-native:location": "northeurope",
            "mock-project:workload_name": "loganalytics",
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


def test_exists() -> None:
    assert az_resource_group is not None


@pulumi.runtime.test
def test_resource_group(request):
    config = request.getfixturevalue("pulumi_project_mock")

    workload_name, env, location, tags = (
        config.get("workload_name"),
        config.get("env"),
        config.get("location"),
        config.get("tags"),
    )

    rg_test = az_resource_group(
        workload_name=workload_name,
        env=env,
        location=location,
        tags=tags,
    )

    def check_parameters(args):
        rg_location, rg_tags = args

        # Check that all tags are present if they are defined
        if tags:
            for key, value in rg_tags.items():
                assert rg_tags.get(key) == value, f"{key} tag is not set to {value}"

        assert rg_location == location, f"location is not set to {location}"

        # pylint: disable=protected-access
        assert rg_test._name == f"rg-{workload_name}-{env}-neu-01"

    return pulumi.Output.all(
        rg_test.location,
        rg_test.tags,
    ).apply(check_parameters)

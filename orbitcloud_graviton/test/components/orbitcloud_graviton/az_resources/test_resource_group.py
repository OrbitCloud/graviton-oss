import pulumi
import pytest

from orbitcloud_graviton.az_resources import az_resource_group
from orbitcloud_graviton.pulumi_mocks import set_mocks

set_mocks()


def test_exists():
    assert az_resource_group is not None, "resource_group is not defined"


@pulumi.runtime.test
@pytest.mark.parametrize(
    "workload_name, env, location, tags",
    [
        ("resourcegroup", "dev", "westeurope", None),
        ("resourcegroup", "dev", "westeurope", {"sometag": "somevalue"}),
    ],
)
def test_resource_group(
    workload_name: str, env: str, location: str, tags: dict[str, str] | None
) -> pulumi.Output:
    rg_test = az_resource_group(
        workload_name=workload_name, env=env, location=location, tags=tags
    )

    def check_parameters(args):
        rg_location, rg_tags = args

        # Check that the env tag is always present
        assert rg_tags.get("env") == env, f"env tag is not set to {env}"

        # Check that all tags are present if they are defined
        if tags:
            for key, value in rg_tags.items():
                assert rg_tags.get(key) == value, f"{key} tag is not set to {value}"

        assert rg_location == location, f"location is not set to {location}"

        assert (
            rg_test._name == f"rg-{workload_name}-{env}-weu-01"
        ), f"rg name is not set to rg-{workload_name}-{env}-weu-01"

    return pulumi.Output.all(
        rg_test.location,
        rg_test.tags,
    ).apply(check_parameters)

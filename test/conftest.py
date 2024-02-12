from uuid import UUID

import pulumi
import pytest

from orbitcloud_graviton.pulumi_lib.azure_base import AzureBase


@pytest.fixture
def stack() -> AzureBase:
    return AzureBase(
        subscription_id=UUID("00000000-0000-0000-0000-000000000000"),
        tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
        location="northeurope",
        workload_name="workload",
        env="test",
    )


@pytest.fixture(scope="session")
def test_stack_params(stack: AzureBase, resource):
    def check(args):
        location, tags = args

        # Check that all tags are present if they are defined
        if tags:
            for key, value in tags.items():
                assert tags.get(key) == value, f"{key} tag is not set to {value}"

        assert location == stack.location, f"location is not set to {stack.location}"

    assert hasattr(resource, "location")
    assert hasattr(resource, "tags")

    pulumi.Output.all(
        resource.location,
        resource.tags,
    ).apply(check)

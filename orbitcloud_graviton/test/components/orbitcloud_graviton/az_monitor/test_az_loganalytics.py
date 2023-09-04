import pulumi
import pytest
from pulumi_azure_native import operationalinsights

from orbitcloud_graviton.az_monitor import az_logworkspace
from orbitcloud_graviton.az_resources import az_resource_group
from orbitcloud_graviton.pulumi_mocks import set_mocks

set_mocks()


@pulumi.runtime.test
@pytest.mark.parametrize(
    "workload_name,env,location,tags",
    [
        ("logworkspace", "dev", "northeurope", None),
        ("logworkspace", "dev", "northeurope", {"sometag": "somevalue"}),
    ],
)
def test_az_logworkspace(workload_name, env, location, tags):
    resource_group = az_resource_group(
        workload_name=workload_name, env=env, location=location, tags=tags
    )

    log_workspace = az_logworkspace(
        workload_name=workload_name,
        env=env,
        location=location,
        resource_group=resource_group,
    )
    assert isinstance(log_workspace, operationalinsights.Workspace)

    def check_parameters(args):
        log_location, log_tags = args

        # Check that the env tag is always present
        assert log_tags.get("env") == env, f"env tag is not set to {env}"

        # Check that all tags are present if they are defined
        if tags:
            for key, value in log_tags.items():
                assert log_tags.get(key) == value, f"{key} tag is not set to {value}"

        assert log_location == location

        assert log_workspace._name.startswith(f"log-{workload_name}-{env}-neu")

    return pulumi.Output.all(
        log_workspace.location,
        log_workspace.tags,
    ).apply(check_parameters)

import pulumi
from pulumi_azure_native import operationalinsights

from orbitcloud_graviton.az_monitor import log_workspace
from orbitcloud_graviton.pulumi_lib import AzureBase


@pulumi.runtime.test
def test_log_logworkspace(stack: AzureBase):
    log = log_workspace(
        workload_name=stack.workload_name,
        env=stack.env,
        location=stack.location,
        resource_group=stack.resource_group,
    )
    assert isinstance(log, operationalinsights.Workspace)

    def check_parameters(args):
        log_location, log_tags = args

        # Check that all tags are present if they are defined
        if stack.tags and log_tags:
            for key, value in log_tags.items():
                assert log_tags.get(key) == value, f"{key} tag is not set to {value}"

        assert log_location == stack.location

        # pylint: disable=protected-access
        assert log._name.startswith(f"log-{stack.workload_name}-{stack.env}-neu")

    return pulumi.Output.all(
        log.location,
        log.tags,
    ).apply(check_parameters)

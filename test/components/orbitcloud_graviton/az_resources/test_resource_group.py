import pulumi
from pulumi_azure_native import resources

from orbitcloud_graviton.pulumi_mocks import set_mocks

set_mocks()

from orbitcloud_graviton.az_resources.rg import resource_group  # noqa
from orbitcloud_graviton.pulumi_lib.azure_base import AzureBase  # noqa


@pulumi.runtime.test
def test_resource_group(
    stack: AzureBase,
) -> None:
    rg: resources.ResourceGroup = resource_group(
        stack=stack,
    )
    assert isinstance(rg, resources.ResourceGroup)
    assert rg._name == f"rg-{stack.workload_name}-{stack.env}-neu-01"

    def check_parameters(stack, rg):
        def check(args):
            location, tags = args

            # Check that all tags are present if they are defined
            if tags:
                for key, value in tags.items():
                    assert tags.get(key) == value, f"{key} tag is not set to {value}"

            assert location == stack.location, f"location is not set to {stack.location}"

        pulumi.Output.all(
            rg.location,
            rg.tags,
        ).apply(check)

    check_parameters(stack, rg)

import pulumi
from pulumi_azure_native import managedidentity

from orbitcloud_graviton.pulumi_lib.azure_base import AzureStack


def user_assigned_id(
    name: str,
    stack: AzureStack,
    opts: pulumi.ResourceOptions | None = None,
) -> managedidentity.UserAssignedIdentity:
    return managedidentity.UserAssignedIdentity(
        resource_name=stack.name_for(
            resource_type=managedidentity.UserAssignedIdentity, workload_name=name
        ),
        args=managedidentity.UserAssignedIdentityArgs(
            resource_group_name=stack.resource_group.name,
            location=stack.location,
        ),
        opts=opts,
    )

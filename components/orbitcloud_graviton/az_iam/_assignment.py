from typing import Optional

from pulumi import ResourceOptions
from pulumi_azure_native import authorization
from pulumi_azuread import ServicePrincipal, User


def role_assignment(
    principal_name: str,
    principal: ServicePrincipal | User,
    role_definition_id: str,
    scope: str,
    opts: Optional[ResourceOptions] = None,
) -> authorization.RoleAssignment:
    # Workaround for creating a unique name for the role assignment
    # as resource_name doesn't accept pulumi Outputs
    role_assignment_name = (
        "role-"
        + principal_name
        + "-"
        + ((principal.translate_input_property("urn") + scope + role_definition_id).encode("utf-8").hex()[:5])
    )

    return authorization.RoleAssignment(
        resource_name=role_assignment_name,
        principal_id=principal.object_id,
        principal_type="ServicePrincipal" if isinstance(principal, ServicePrincipal) else "User",
        role_definition_id=role_definition_id,
        scope=scope,
        opts=opts,
    )

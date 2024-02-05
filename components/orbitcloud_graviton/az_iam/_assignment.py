from typing import Optional

import pulumi
import pulumi_azuread as azuread
from pulumi_azure_native import authorization

from ._roles import get_role_id_by_name


def iam_assignment(
    resource_name: str,
    role_name: str,
    scope: str,
    principal: azuread.ServicePrincipal | azuread.User | azuread.Group,
    opts: Optional[pulumi.ResourceOptions] = None,
) -> authorization.RoleAssignment:
    role_definition_id = get_role_id_by_name(role_name)

    return authorization.RoleAssignment(
        resource_name=resource_name,
        principal_id=principal.object_id,
        principal_type=authorization.PrincipalType(type(principal).__name__),
        role_definition_id=role_definition_id,
        scope=scope,
        opts=opts,
    )

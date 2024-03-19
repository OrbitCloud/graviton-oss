from typing import Optional, Union

import pulumi
from pulumi_azure_native import authorization
from pydantic import BaseModel, ConfigDict

from orbitcloud_graviton.az_lib.types import AzureIdRef
from orbitcloud_graviton.pulumi_lib.azure_base import AzureBase
from orbitcloud_graviton.pulumi_lib.helpers import fmt_name

from ._roles import get_role_id_by_name


class IamAssignmentConfig(BaseModel):
    name_prefix: Optional[str] = None
    role: str
    scope: AzureIdRef
    description: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


def iam_assignment(
    stack: AzureBase,
    config: IamAssignmentConfig,
    principal_id: Union[str, pulumi.Output[str]],
    principal_type: str = "ServicePrincipal",
    opts: Optional[pulumi.ResourceOptions] = None,
) -> authorization.RoleAssignment:
    role_definition_id = get_role_id_by_name(config.role)

    if config.name_prefix:
        workload_name: str = fmt_name([config.name_prefix, config.role.lower()])
    else:
        workload_name = fmt_name([stack.workload_name, config.role.lower()])

    return authorization.RoleAssignment(
        resource_name=stack.name_for(
            resource_type=authorization.RoleAssignment, workload_name=workload_name
        ),
        principal_id=principal_id,
        principal_type=principal_type,
        role_definition_id=role_definition_id,
        scope=config.scope,
        description=config.description,
        opts=opts,
    )

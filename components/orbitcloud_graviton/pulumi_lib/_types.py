from typing import Annotated, Type, Union

import pulumi
from pydantic import AfterValidator

from orbitcloud_graviton.az_lib.types import AzureResourceId


def parse_stack_reference(v: str) -> tuple[str, str]:
    parts: list[str] = v.removeprefix("stack://").split("/")
    if len(parts) < 3:
        raise ValueError(
            f"{v} is not a valid stack reference (stack://project_name/stack_name/output_name)"
        )
    # If organization is included stack://organization_name/project_name/stack_name/output_name
    if len(parts) == 4:
        stack_ref = parts[0] + "/" + parts[1] + "/" + parts[2]
        output_name = parts[3]
    else:
        stack_ref = pulumi.get_organization() + "/" + parts[0] + "/" + parts[1]
        output_name = parts[2]
    return stack_ref, output_name


def get_resource_id(v: Union[str, Type[pulumi.Output], Type[pulumi.CustomResource]]):
    if isinstance(v, str):
        if v.startswith("/subscriptions") and AzureResourceId.is_valid(v):
            return AzureResourceId(v).id

        if v.startswith("stack://"):
            stack_ref, output_name = parse_stack_reference(v)
            stack_output = pulumi.StackReference(stack_ref).require_output(output_name)
            return stack_output

    if isinstance(v, pulumi.Output):
        if v.is_known():
            return v
        else:
            return v.apply(lambda x: x)

    if isinstance(v, pulumi.CustomResource):
        if hasattr(v, "id") and v.id.is_known():
            return v.id
        else:
            raise ValueError(f"Unable to resolve resource ID of pulumi.CustomResource {v}")
    raise ValueError(f"{v} is not a valid resource ID reference")


IdReference = Annotated[
    Union[pulumi.Output, pulumi.CustomResource, str],
    AfterValidator(get_resource_id),
]

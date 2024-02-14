import re
from functools import reduce
from typing import Annotated, Any, Union
from uuid import UUID

import pulumi
from pulumi.runtime.sync_await import _sync_await
from pulumi_azure_native import resources
from pydantic import AfterValidator, GetCoreSchemaHandler, ValidationInfo
from pydantic_core import core_schema


class AzureResourceId:
    def __init__(self, id: str) -> None:
        self.id: str = id
        params: dict[str, str] = self._params()

        self.subscription_id = UUID(params["subscriptionId"])
        self.resource_group_name: str | None = params.get("resource_group_name")
        self.provider: str | None = params.get("provider")
        self.resource_type: str | None = params.get("resource_type")
        self.resource_name: str | None = params.get("resource_name")
        self.sub_resource: str | None = params.get("sub_resource")

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str):
            return self.id == other
        return self.id == other.id

    def __str__(self) -> str:
        return self.id

    def get_resource(self) -> resources.AwaitableGetResourceResult:
        raise NotImplementedError(
            "Not implemented until https://github.com/pulumi/pulumi-azure-native/issues/2630 is fixed."
        )  # pragma: no cover
        # return resources.get_resource(
        #     resource_group_name=self.resource_group_name,
        #     resource_provider_namespace=self.provider,
        #     resource_type=self.resource_type,
        #     resource_name=self.resource_name,
        # )

    @staticmethod
    def is_valid(value: str) -> bool:
        pattern = r"^/subscriptions/([^/]+)(?:/resourceGroups/([^/]+))?(?:/providers/([^/]+)/([^/]+)/([^/]+)(?:/(.*))?)?$"
        if re.match(pattern, value):
            return True
        return False

    @classmethod
    def validate(cls, value: str, info: ValidationInfo):
        if not cls.is_valid(value):
            raise ValueError("Invalid Azure Resource ID")
        return cls(value)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.with_info_after_validator_function(
            function=cls.validate, schema=handler(str), field_name=handler.field_name
        )

    def _params(self) -> dict[str, str]:
        pattern = r"^/subscriptions/([^/]+)(?:/resourceGroups/([^/]+))?(?:/providers/([^/]+)/([^/]+)/([^/]+)(?:/(.*))?)?$"
        match: re.Match[str] | None = re.match(pattern, self.id)

        if not match:
            raise ValueError("Invalid Azure Resource ID")

        groups: tuple[str | Any, ...] = match.groups()
        keys = [
            "subscriptionId",
            "resource_group_name",
            "provider",
            "resource_type",
            "resource_name",
            "sub_resource",
        ]
        return {key: value for key, value in zip(keys, groups) if value is not None}


def parse_stack_reference(v: str) -> tuple[str, str]:
    parts: list[str] = v.removeprefix("stack://").split("/")
    if len(parts) < 3 or len(parts) > 4:
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


def deep_get(obj: dict, path, default=None) -> Any | None:
    return reduce(
        lambda d, key: d.get(key, default) if isinstance(d, dict) else default,
        path.split("."),
        obj,
    )


def get_resource_id(
    v: Union[pulumi.Output[str], str],
) -> str | pulumi.Output[str]:
    if isinstance(v, pulumi.Output):
        return v if v.is_known() else v.apply(lambda x: x)

    if v.startswith("/subscriptions"):
        return AzureResourceId(v).id

    if v.startswith("stack://"):
        stack_ref, output_name = parse_stack_reference(v)

        if "." in output_name:
            stack = pulumi.StackReference(name=v, stack_name=stack_ref)
            parent: str = output_name.split(".")[0]
            path: str = ".".join(output_name.split(".")[1:])

            # Workaround until Pulumi supports async methods in Python
            # https://github.com/pulumi/pulumi/issues/12172#issuecomment-1691499199
            output: Any | type[None] | None = _sync_await(
                awaitable=stack.get_output_details(name=parent),
            ).value

            if output and isinstance(output, dict):
                child: Any | None = deep_get(output, path=path)
                if child:
                    return str(child)
                raise ValueError(f"Key path {output_name} not found in stack {stack_ref}")

        stack_output: pulumi.Output[str] = pulumi.StackReference(stack_ref).require_output(
            name=output_name
        )

        return stack_output if stack_output.is_known() else stack_output.apply(lambda x: x)

    raise ValueError(f"{v} is not a valid resource ID reference")


def get_resource_name(
    v: Union[pulumi.Output[str], str],
    info: ValidationInfo,
) -> str | pulumi.Output[str] | None:
    if isinstance(v, pulumi.Output):
        if v.is_known():
            return v
        else:
            return v.apply(lambda x: x)

    if v.startswith("/subscriptions"):
        return AzureResourceId(v).resource_name

    if v.startswith("stack://"):
        stack_ref, output_name = parse_stack_reference(v)

        stack_output: pulumi.Output[str] = pulumi.StackReference(stack_ref).require_output(
            name=output_name
        )
        if stack_output.is_known():
            return stack_output
        else:
            return stack_output.apply(lambda x: x)

    raise ValueError(f"{v} is not a valid resource name reference")


AzureIdRef = Annotated[
    Union[str, pulumi.Output[str]],
    AfterValidator(func=get_resource_id),
]

AzureNameRef = Annotated[
    Union[str, pulumi.Output[str]],
    AfterValidator(func=get_resource_name),
]

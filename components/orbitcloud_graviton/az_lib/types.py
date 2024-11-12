import re
from functools import reduce
from typing import (
    Annotated,
    Any,
    Optional,
    Union,
)
from uuid import UUID

import pulumi
from pulumi.runtime.sync_await import _sync_await
from pulumi_azure_native import resources
from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    Field,
    GetCoreSchemaHandler,
    SecretStr,
    ValidationInfo,
)
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
        pattern = r"(?i)^/subscriptions/([^/]+)(?:/resourceGroups/([^/]+))?(?:/providers/([^/]+)/([^/]+)/([^/]+)(?:/(.*))?)?$"
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
        pattern = r"(?i)^/subscriptions/([^/]+)(?:/resourceGroups/([^/]+))?(?:/providers/([^/]+)/([^/]+)/([^/]+)(?:/(.*))?)?$"
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


def parse_stack_reference(v: str) -> tuple[str, str, Optional[str]]:
    parts: list[str] = v.removeprefix("stack://").split("/")
    path = None
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

    if "." in output_name:
        path = ".".join(output_name.split(".")[1:])
        output_name = output_name.split(".")[0]

    return stack_ref, output_name, path


def deep_get(obj: dict, path, default=None) -> Any | None:
    return reduce(
        lambda d, key: d.get(key, default) if isinstance(d, dict) else default,
        path.split("."),
        obj,
    )


known_stacks: dict[str, pulumi.StackReference] = {}


def get_stack_output(ref):
    if not ref.startswith("stack://"):
        raise ValueError(f"{ref} is not a valid stack reference")

    stack_ref, output_name, path = parse_stack_reference(ref)
    if stack_ref in known_stacks:
        stack: pulumi.StackReference = known_stacks[stack_ref]
    else:
        stack = pulumi.StackReference(name=ref, stack_name=stack_ref)
        known_stacks[stack_ref] = stack

    # Workaround until Pulumi supports async methods in Python
    # https://github.com/pulumi/pulumi/issues/12172#issuecomment-1691499199
    output: Any | type[None] | None = _sync_await(
        awaitable=stack.get_output_details(name=output_name),
    )

    if isinstance(output, pulumi.StackReferenceOutputDetails):
        output_value = output.secret_value if output.secret_value else output.value

    if isinstance(output_value, dict) and path:
        output_value = deep_get(output_value, path=path)

    if output_value is None:
        raise ValueError(f"Output not found in stack {stack_ref=} {output_name=} {path=}")

    return output_value


def get_resource_id(v: Union[pulumi.Output[str], str]) -> str | pulumi.Output[str]:
    if isinstance(v, pulumi.Output):
        return v if v.is_known() else v.apply(lambda x: x)

    if v.startswith("/subscriptions"):
        return AzureResourceId(id=v).id

    if v.startswith("stack://"):
        return str(get_stack_output(ref=v))

    raise ValueError(f"{v} is not a valid resource ID reference")


#
# Pulumi secrets are stored as a dictionary with a single key "secure"
# the actual value will be resolved at runtime but we need to allow for
# the dictionary structure for schema validation purposes
#
class _PulumiSecretSchemaObject(BaseModel):
    secure: str


PulumiSecretField = Field(json_schema_extra=_PulumiSecretSchemaObject.model_json_schema())

AzureIdRef = Annotated[
    Union[str, pulumi.Output[str]],
    AfterValidator(func=get_resource_id),
]

StrRef = Annotated[
    Union[str, pulumi.Output],
    PulumiSecretField,
    AfterValidator(func=get_stack_output),
]
SecretStrRef = Annotated[
    Union[SecretStr, pulumi.Output[str]],
    PulumiSecretField,
    AfterValidator(func=get_stack_output),
]

DictRef = Annotated[
    Union[dict[str, Any], str],
    BeforeValidator(func=get_stack_output),
]

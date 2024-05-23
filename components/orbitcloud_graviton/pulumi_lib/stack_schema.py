import json
from copy import deepcopy
from typing import Any, Callable, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, create_model
from pydantic.fields import FieldInfo

from orbitcloud_graviton.pulumi_lib import AzureStack

T = TypeVar("T", bound="BaseModel")


def _make_optional(
    include: Optional[list[str]] = None, exclude: Optional[list[str]] = None
) -> Callable[[type[T]], type[T]]:
    """Return a decorator to make Pydantic model fields optional"""

    if exclude is None:
        exclude = []

    def decorator(model: type[T]) -> type[T]:
        def make_optional(field: FieldInfo, default: Any = None) -> tuple[Any, FieldInfo]:
            new = deepcopy(field)
            new.default = default
            new.annotation = Optional[field.annotation or Any]
            return new.annotation, new

        fields = model.model_fields
        if include is None:
            fields = fields.items()
        else:
            fields = ((k, v) for k, v in fields.items() if k in include)

        return create_model(
            model.__name__,
            __base__=model,
            __module__=model.__module__,
            **{
                field_name: make_optional(field_info)
                for field_name, field_info in fields
                if exclude is None or field_name not in exclude
            },  # type: ignore
        )

    return decorator


def generate_stack_schema(model, output_file: str):
    # Edit AzureBase to have all fields optional except workload_name
    # as other fields can be set by the Pulumi ESC environment
    @_make_optional(exclude=["workload_name"])
    class OptionalAzureBase(AzureStack):
        azuread_tenant_id: UUID = Field(..., validation_alias="azuread:tenantId")

    ConfigObject = create_model(
        "PulumiStackConfig", __base__=type("_config", (model, OptionalAzureBase), {})
    )

    # Representation of a Pulumi.stack.yaml file
    class PulumiStackConfig(BaseModel):
        environment: Optional[list[str]] = None
        config: ConfigObject

        model_config = ConfigDict(extra="forbid")

    config_schema: dict[str, Any] = TypeAdapter(PulumiStackConfig).json_schema()

    # Write the schema to a file
    with open(file=output_file, mode="w") as f:
        f.write(json.dumps(config_schema, indent=2) + "\n")

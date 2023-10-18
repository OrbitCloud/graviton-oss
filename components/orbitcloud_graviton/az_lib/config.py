from dataclasses import MISSING, Field, dataclass, field, fields, is_dataclass
from typing import (
    Annotated,
    Any,
    Callable,
    Collection,
    Dict,
    Optional,
    Protocol,
    Type,
    get_args,
    get_origin,
)

import pulumi
from beartype.door import is_subhint


# pylint: disable=too-few-public-methods
class ConfigProtocol(Protocol):
    workload_name: str
    env: str
    location: str
    tags: Optional[Dict[str, str]]
    resource_group_name: Optional[str]


@dataclass(kw_only=True, frozen=True)
class StackConfig(ConfigProtocol):
    workload_name: str
    env: str
    location: Annotated[str, "azure-native"]
    tags: Optional[Dict[str, str]] = field(compare=False, default_factory=lambda: {})
    resource_group_name: Optional[str] = None


@dataclass
class Confy:
    dataclass_obj: Any

    @staticmethod
    def field_type(field_type: Any) -> Type:
        # Unwrap Optional[]
        field_type = (
            field_type.__args__[0] if field_type == Optional[field_type] else field_type
        )

        # Unwrap Annotated[]
        field_type = (
            get_args(field_type)[0]
            if get_origin(field_type) is Annotated
            else field_type
        )

        if field_type in [str, int, bool]:
            return field_type

        if is_subhint(field_type, dict | list | tuple):
            return Collection

        raise ValueError(f"Unsupported field data type: {field_type}")

    @staticmethod
    def is_azure_native(field_type: Any) -> bool:
        if field_type == Optional[field_type]:
            field_type = field_type.__args__[0]

        return get_origin(field_type) is Annotated and "azure-native" in get_args(
            field_type
        )

    @staticmethod
    def is_secret(field_type: Any) -> bool:
        if field_type == Optional[field_type]:
            field_type = field_type.__args__[0]

        return get_origin(field_type) is Annotated and "secret" in get_args(field_type)

    @staticmethod
    def is_optional(field_type: Any) -> bool:
        return field_type == Optional[field_type]

    @classmethod
    def config_getter_func(
        cls,
        dcfield: Field,
        config: pulumi.Config,
    ) -> Callable:
        is_optional = cls.is_optional(dcfield.type)
        is_secret: bool = cls.is_secret(dcfield.type)
        field_type = cls.field_type(dcfield.type)

        getter_func_name: str = "get" if is_optional else "require"

        if is_secret:
            getter_func_name += "_secret"

        if field_type is Collection:
            getter_func_name += "_object"
        elif field_type is bool:
            getter_func_name += "_bool"
        elif field_type is int:
            getter_func_name += "_int"
        elif field_type is str:
            pass
        else:
            raise ValueError(f"Unsupported config getter for field type: {field_type}")

        if hasattr(config, getter_func_name):
            return getattr(config, getter_func_name)

        raise ValueError(
            f"Could not find getter function {getter_func_name} in pulumi.Config"
        )

    @staticmethod
    def default_value(dcfield: Field) -> Any:
        if dcfield.default_factory is not MISSING:
            return dcfield.default_factory()
        if dcfield.default is not MISSING:
            return dcfield.default

        return None

    @staticmethod
    def field_info(dcfield: Field) -> Dict[str, Any]:
        return {
            "name": dcfield.name,
            "type": dcfield.type,
            "default_factory": dcfield.default_factory,
            "default": dcfield.default,
        }

    def __post_init__(self) -> None:
        if not is_dataclass(self.dataclass_obj):
            raise ValueError("dataclass_type must be a dataclass type")

        self.dckwargs: dict[str, Any] = {}

        self.pulumi_config = pulumi.Config()
        self.pulumi_azure_config = pulumi.Config("azure-native")

    # Returns the same type as the dataclass_type
    def populate(self) -> Any:
        for dcfield in fields(self.dataclass_obj):
            config_instance = (
                self.pulumi_azure_config
                if self.is_azure_native(dcfield.type)
                else self.pulumi_config
            )

            getter_func = self.config_getter_func(
                dcfield=dcfield,
                config=config_instance,
            )

            field_value = getter_func(dcfield.name)

            if field_value is None:
                field_value = self.default_value(dcfield)

            self.dckwargs.update({dcfield.name: field_value})

        return self.dataclass_obj(**self.dckwargs)

from typing import Annotated, Dict, Optional, Any, Type, get_args, get_origin
from dataclasses import dataclass, field, fields, is_dataclass, make_dataclass
import pulumi


@dataclass
class BaseConfig:
    workload_name: str
    env: str
    location: Annotated[str, "azure-native"]
    tags: Optional[Dict[str, str]] = field(default_factory=dict)


@dataclass
class StackConfig:
    dataclass_type: Optional[Type] = None

    def _field_is_optional(self, field_type: Any) -> bool:
        return field_type == Optional[field_type]

    def _is_annotated_with(self, field_type: Any, annotation: str) -> bool:
        if get_origin(field_type) is Annotated:
            return annotation in get_args(field_type)
        return False

    def __post_init__(self) -> None:
        if not is_dataclass(self.dataclass_type):
            raise ValueError("dataclass_type must be a dataclass type")

        config = pulumi.Config()
        azure_config = pulumi.Config("azure-native")

        field_definitions = []

        for field_info in fields(self.dataclass_type):
            field_name = field_info.name
            field_type = field_info.type

            is_optional = self._field_is_optional(field_type)

            is_bool = field_type is bool

            is_int = field_type is int or (
                is_optional and field_type.__args__[0] is int
            )

            is_azure_native: bool = self._is_annotated_with(field_type, "azure-native")

            is_secret: bool = self._is_annotated_with(field_type, "secret")

            is_object: bool = (
                field_type is dict
                or field_type is list
                or field_type is tuple
                or field_type is set
            )

            if is_azure_native:
                value = (
                    azure_config.get(field_name)
                    if is_optional
                    else azure_config.require(field_name)
                )
            elif is_object:
                if is_secret:
                    value = (
                        config.get_secret_object(field_name)
                        if is_optional
                        else config.require_secret_object(field_name)
                    )
                else:
                    value = (
                        config.get_object(field_name)
                        if is_optional
                        else config.require_object(field_name)
                    )
            elif is_secret:
                value = (
                    config.get_secret(field_name)
                    if is_optional
                    else config.require_secret(field_name)
                )
            elif is_bool:
                value = (
                    config.get_bool(field_name)
                    if is_optional
                    else config.require_bool(field_name)
                )
            elif is_int:
                value = (
                    config.get_int(field_name)
                    if is_optional
                    else config.require_int(field_name)
                )
            else:
                value = (
                    config.get(field_name)
                    if is_optional
                    else config.require(field_name)
                )
            field_definitions.append((field_name, field_type, field(default=value)))
        GeneratedConfig: type = make_dataclass("GeneratedConfig", field_definitions)
        self.get_config = GeneratedConfig()

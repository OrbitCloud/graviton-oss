import inspect
from typing import (
    Annotated,
    Any,
    Collection,
    Dict,
    Optional,
    Tuple,
    Type,
    get_args,
    get_origin,
)

import pulumi
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
)


class PulumiConfigSettingsSource(PydanticBaseSettingsSource):
    def config_path(self, field: FieldInfo, field_name: str, bag: Optional[str] = "") -> tuple[pulumi.Config, str]:
        alias = field.validation_alias if isinstance(field.validation_alias, str) else field_name

        if ":" in alias:
            bag, alias = alias.split(":")

        config = pulumi.Config(bag)
        return config, alias

    def is_model_class(self, field: FieldInfo) -> bool:
        if not field.annotation:
            return False
        if inspect.isclass(field.annotation):
            return issubclass(field.annotation, BaseModel)

        return False

    def get_field_type(self, field_type: Type) -> Type:
        # Unwrap Optional[]
        field_type = get_args(field_type)[0] if field_type == Optional[field_type] else field_type

        # Unwrap Annotated[]
        field_type = get_args(field_type)[0] if get_origin(field_type) is Annotated else field_type

        if field_type in [str, int, bool]:
            return field_type

        if field_type in [list, dict, set, tuple] or get_origin(field_type) in [
            list,
            dict,
            set,
            tuple,
        ]:
            return Collection

        return field_type

    def get_field_value(
        self,
        field: FieldInfo,
        field_name: str,
        config_bag: Optional[str] = None,
    ):
        config, alias = self.config_path(field, field_name, config_bag)
        field_type = self.get_field_type(field.annotation) if field.annotation else None

        if field_type is Collection or self.is_model_class(field):
            return config.get_object(alias), field_name, True

        return config.get(alias), field_name, False

    def __call__(self) -> Dict[str, Any]:
        pulumi_config_bag = getattr(self.settings_cls.model_config, "pulumi_config_bag", None)

        d = {
            field_name: self.get_field_value(field, field_name, pulumi_config_bag)
            for field_name, field in self.settings_cls.model_fields.items()
        }

        return d


class PulumiConfig(BaseSettings):
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            PulumiConfigSettingsSource(settings_cls),
        )

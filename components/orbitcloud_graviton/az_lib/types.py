import re
from typing import Any
from uuid import UUID

from pydantic import GetCoreSchemaHandler, ValidationInfo
from pydantic_core import core_schema


class AzureResourceId:
    def __init__(self, id) -> None:
        self.id = id
        params = self._params()

        self.subscription_id = UUID(params["subscriptionId"])
        self.resource_group_name: str | None = params.get("resource_group_name")
        self.provider: str | None = params.get("provider")
        self.resource_type: str | None = params.get("resource_type")
        self.resource_name: str | None = params.get("resource_name")
        self.sub_resource: str | None = params.get("sub_resource")

    def __str__(self) -> str:
        return self.id

    def scope_repr(self) -> str:
        if self.sub_resource is not None:
            return f"{self.resource_name}-{self.sub_resource}"
        if self.resource_name is not None:
            return self.resource_name
        if self.resource_group_name is not None:
            return self.resource_group_name
        return f"subscription-{str(self.subscription_id)[:5]}"

    @classmethod
    def validate(cls, value, info: ValidationInfo):
        pattern = r"^/subscriptions/([^/]+)(?:/resourceGroups/([^/]+))?(?:/providers/([^/]+)/([^/]+)/([^/]+)(?:/([^/]+))?)?$"
        if not re.match(pattern, value):
            raise ValueError("Invalid Azure Resource ID")
        return cls(value)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.with_info_after_validator_function(
            cls.validate, handler(str), field_name=handler.field_name
        )

    def _params(self) -> dict[str, str]:
        pattern = r"^/subscriptions/([^/]+)(?:/resourceGroups/([^/]+))?(?:/providers/([^/]+)/([^/]+)/([^/]+)(?:/([^/]+))?)?$"
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

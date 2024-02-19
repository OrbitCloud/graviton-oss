from functools import lru_cache
from typing import Any, Dict, Optional, Type
from uuid import UUID

import pulumi
from pulumi_azure_native import resources
from pydantic import Field
from pydantic_settings import SettingsConfigDict

from orbitcloud_graviton.az_lib import resource_namer
from orbitcloud_graviton.az_resources import resource_group

from .config import PulumiConfig


class AzureBase(PulumiConfig):
    subscription_id: UUID = Field(..., validation_alias="azure-native:subscriptionId")
    tenant_id: UUID = Field(..., validation_alias="azure-native:tenantId")
    location: str = Field(..., validation_alias="azure-native:location")

    env: str
    workload_name: str = Field(
        ...,
        title="Workload Name",
        description="The name of the workload, used for naming resources",
    )
    tags: Optional[Dict[str, str]] = None

    skip_exports: Optional[bool] = False
    exports_prefix: Optional[str] = ""

    resource_group_name: Optional[str] = None
    _resource_group: Optional[resources.ResourceGroup] = None

    @property
    def resource_group(self) -> resources.ResourceGroup:
        if self._resource_group:
            return self._resource_group

        self._resource_group = resource_group(stack=self)
        pulumi.export("resource_group_id", self._resource_group.id)
        pulumi.export("resource_group_name", self._resource_group.name)
        return self._resource_group

    def name_for(self, resource_type: Type, workload_name: Optional[str] = None) -> str:
        return resource_namer(
            resource_type=resource_type,
            workload_name=workload_name or self.workload_name,
            env=self.env,
            location=self.location,
        )

    def export(self, exports: Dict[str, Any]) -> None:
        for k, v in exports.items():
            pulumi.export(name=f"{self.exports_prefix}_{k}", value=v)

    model_config = SettingsConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


@lru_cache
def get_azure_stack() -> AzureBase:
    stack = AzureBase.model_validate({})
    if not stack.skip_exports:
        pulumi.export(
            name="stack",
            value={
                "workload_name": stack.workload_name,
                "subscription_id": str(stack.subscription_id),
                "tenant_id": str(stack.tenant_id),
                "location": stack.location,
                "env": stack.env,
            },
        )
    return stack


class EntraBase(PulumiConfig):
    tenant_id: UUID = Field(..., alias="azuread:tenantId")
    model_config = SettingsConfigDict(populate_by_name=True)

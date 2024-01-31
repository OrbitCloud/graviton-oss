from functools import lru_cache
from typing import Dict, Optional, Type
from uuid import UUID

from pulumi_azure_native import resources
from pydantic import Field
from pydantic_settings import SettingsConfigDict

from orbitcloud_graviton.az_lib import resource_namer
from orbitcloud_graviton.az_resources import resource_group

from ._config import PulumiConfig


class AzureBase(PulumiConfig):
    subscription_id: UUID = Field(..., alias="azure-native:subscriptionId")
    tenant_id: UUID = Field(..., alias="azure-native:tenantId")
    location: str = Field(..., alias="azure-native:location")

    env: str
    workload_name: str
    tags: Optional[Dict[str, str]] = None

    resource_group_name: Optional[str] = None
    _resource_group: Optional[resources.ResourceGroup] = None

    @property
    def resource_group(self) -> resources.ResourceGroup:
        if self._resource_group:
            return self._resource_group

        self._resource_group = resource_group(self)
        return self._resource_group

    def name_for(self, resource_type: Type, workload_name: Optional[str] = None) -> str:
        return resource_namer(
            resource_type=resource_type,
            workload_name=workload_name or self.workload_name,
            env=self.env,
            location=self.location,
        )

    model_config = SettingsConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


@lru_cache
def get_azure_stack() -> AzureBase:
    return AzureBase.model_validate({})

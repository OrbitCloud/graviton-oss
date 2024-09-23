from functools import lru_cache
from typing import Any, Dict, Optional, Type
from uuid import UUID

import pulumi
from pulumi_azure_native import Provider, resources
from pydantic import BaseModel, Field
from pydantic_settings import SettingsConfigDict

from orbitcloud_graviton.az_lib import resource_namer
from orbitcloud_graviton.az_resources import resource_group

from .config import PulumiConfig


class EntraEscApp(BaseModel):
    name: str
    app_client_id: UUID
    app_object_id: UUID
    service_principal_id: UUID
    service_principal_object_id: UUID


class AzureEnvironmentPulumiConfig(BaseModel):
    pulumi_esc_app: EntraEscApp
    resource_group_name: str
    tags: dict[str, str] | None = None


class AzureStack(PulumiConfig):
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

    azure_environment: AzureEnvironmentPulumiConfig | None = None

    skip_exports: Optional[bool] = False
    exports_prefix: Optional[str] = None

    resource_group_name: Optional[str] = None
    resource_group_id: Optional[str] = None
    _resource_group: Optional[resources.ResourceGroup] = None

    _providers: Optional[Dict[str, pulumi.ResourceOptions]] = None

    @property
    def resource_group(self) -> resources.ResourceGroup:
        if self._resource_group:
            return self._resource_group

        self._resource_group = resource_group(stack=self)
        return self._resource_group

    def name_for(self, resource_type: Type, workload_name: Optional[str] = None) -> str:
        return resource_namer(
            resource_type=resource_type,
            workload_name=workload_name or self.workload_name,
            env=self.env,
            location=self.location,
        )

    def subscription_provider(
        self, subscription_id: UUID, merge_opts: Optional[pulumi.ResourceOptions] = None
    ) -> pulumi.ResourceOptions:
        if not self._providers:
            self._providers = {}
        if str(subscription_id) in self._providers:
            provider = self._providers[str(object=subscription_id)]
        else:
            provider = pulumi.ResourceOptions(
                provider=Provider(
                    resource_name=f"azure-native-{subscription_id}",
                    subscription_id=str(object=subscription_id or self.subscription_id),
                )
            )
            self._providers[str(subscription_id)] = provider

        if merge_opts:
            provider: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
                opts1=provider, opts2=merge_opts
            )

        return provider

    def export(self, exports: Dict[str, Any], prefix=None) -> None:
        if not self.skip_exports:
            pre: str | None = prefix or self.exports_prefix
            for k, v in exports.items():
                key: str = f"{pre}_{k}" if pre else k
                pulumi.export(name=key, value=v)

    model_config = SettingsConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


@lru_cache
def get_azure_stack() -> AzureStack:
    stack: AzureStack = AzureStack.model_validate({})
    if not stack.skip_exports:
        stack.export(
            exports={
                "stack": {
                    "workload_name": stack.workload_name,
                    "subscription_id": str(stack.subscription_id),
                    "fq_subscription_id": f"/subscriptions/{stack.subscription_id}",
                    "tenant_id": str(stack.tenant_id),
                    "location": stack.location,
                    "env": stack.env,
                    "resource_group_name": stack.resource_group.name,
                    "resource_group_id": stack.resource_group.id,
                }
            }
        )

    return stack


class EntraStack(PulumiConfig):
    tenant_id: UUID = Field(..., alias="azuread:tenantId")
    model_config = SettingsConfigDict(populate_by_name=True)


@lru_cache
def get_entra_stack() -> EntraStack:
    return EntraStack.model_validate({})

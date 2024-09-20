from typing import Literal, Optional
from uuid import UUID

import pulumi
from pulumi_azure_native.azureactivedirectory import v20230517preview as entra
from pydantic import BaseModel, ConfigDict

from orbitcloud_graviton.pulumi_lib import AzureStack, EntraStack


class ExternalIdTenantConfig(BaseModel):
    location: Literal["Europe", "United States", "Asia Pacific", "Australia", "Japan"] = "Europe"
    country_code: str = "IS"
    display_name: str
    initial_domain_prefix: str
    tenant_id: UUID

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ExternalIdTenant(pulumi.ComponentResource):
    def __init__(
        self,
        stack: AzureStack,
        entra_config: EntraStack,
        config: ExternalIdTenantConfig,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        self.stack: AzureStack = stack
        self.config: ExternalIdTenantConfig = config
        self.entra_config: EntraStack = entra_config

        super().__init__(
            "Graviton:ExternalIdTenant",
            name=f"externalidtenant-{stack.workload_name}-{stack.env}",
            props=None,
            opts=opts,
        )

        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts1=opts, opts2=pulumi.ResourceOptions(parent=self)
        )

        self.tenant: entra.CIAMTenant = self._tenant()

        self._outputs()

    def _tenant(self) -> entra.CIAMTenant:
        return entra.CIAMTenant(
            resource_name=self.config.initial_domain_prefix,
            resource_name_=self.config.initial_domain_prefix,
            resource_group_name=self.stack.resource_group.name,
            location=self.config.location,
            sku=entra.CIAMResourceSKUArgs(
                name=entra.CIAMResourceSKUName.STANDARD,
                tier=entra.CIAMResourceSKUTier.A0,
            ),
            create_tenant_properties=entra.CreateCIAMTenantPropertiesArgs(
                display_name=self.config.display_name,
                country_code=self.config.country_code,
            ),
            tenant_id=str(self.config.tenant_id),
            opts=self._opts,
        )

    def _outputs(self) -> None:
        self.register_outputs(
            outputs={"tenant": self.tenant},
        )

        self.stack.export(
            exports={
                "tenant": {
                    "id": self.tenant.id,
                    "name": self.tenant.name,
                }
            }
        )

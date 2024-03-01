from typing import List, Optional

import pulumi
from pulumi import ComponentResource, ResourceOptions
from pulumi_azure_native import insights, keyvault
from pydantic import BaseModel, ConfigDict, Field, model_validator

from orbitcloud_graviton.az_lib.types import AzureIdRef
from orbitcloud_graviton.az_monitor.az_diagnosticsetting import diagnostic_setting
from orbitcloud_graviton.az_network.types import PublicIPv4Network
from orbitcloud_graviton.pulumi_lib import AzureBase


class KeyVaultConfig(BaseModel):
    name: Optional[str] = Field(
        default=None,
        title="Explicitly set Key Vault name",
        description="The name of the Key Vault. If not set, a name will be generated.",
    )
    public_network_access: keyvault.PublicNetworkAccess = Field(
        default=keyvault.PublicNetworkAccess.DISABLED,
        title="Public Network Access",
        description="Whether the key vault is accessible from public networks.",
    )
    allowed_private_subnets: Optional[List[AzureIdRef]] = Field(
        default=None,
        title="Allowed private subnets",
        description="Allows network access from a list of Private Subnets",
        examples=[
            "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-name/providers/Microsoft.Network/virtualNetworks/vnet-name/subnets/subnet-name"
            "stack://project/stack-name/output-name",
            "stack://project/stack-name/output-name.subnet_id",
            "stack://project/stack-name/output-name.subnets.subnet_id",
        ],
    )
    allowed_public_networks: Optional[List[PublicIPv4Network]] = Field(
        default=None,
        title="Allowed public networks",
        description="Allows network access from a list of Public Networks. Must be in CIDR notation.",
        examples=["157.157.205.0/24", "103.103.10.5/32"],
    )
    allow_azure_services: Optional[bool] = Field(
        default=True,
        title="Allow Azure Services",
        description="Allow traffic from trusted Azure services",
    )

    log_workspace_id: Optional[AzureIdRef] = None

    @model_validator(mode="after")
    def validate_network_access(m: "KeyVaultConfig") -> "KeyVaultConfig":
        if m.public_network_access == keyvault.PublicNetworkAccess.ENABLED:
            if m.allowed_private_subnets is None and m.allowed_public_networks is None:
                pulumi.warn(
                    msg="KeyVault is configured to allow public network access, \
                        but no private subnets or public networks are allowed \
                        and default action is set to deny."
                )
        return m

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class KeyVault(ComponentResource):
    def __init__(
        self,
        stack: AzureBase,
        config: KeyVaultConfig,
        opts: Optional[ResourceOptions] = None,
    ) -> None:
        self.stack: AzureBase = stack
        self.config: KeyVaultConfig = config

        super().__init__(
            "Graviton:az_keyvault:KeyVault", name=f"kv-{stack.workload_name}", props=None, opts=opts
        )

        self.vault: keyvault.Vault = self._vault()
        self._diagnostic_settings()
        self._outputs()

    def _vault(self) -> keyvault.Vault:
        return keyvault.Vault(
            resource_name=self.stack.name_for(resource_type=keyvault.Vault),
            vault_name=self.config.name,
            resource_group_name=self.stack.resource_group.name,
            location=self.stack.location,
            properties=keyvault.VaultPropertiesArgs(
                public_network_access=self.config.public_network_access,
                enable_rbac_authorization=True,
                tenant_id=str(self.stack.tenant_id),
                sku=keyvault.SkuArgs(
                    family=keyvault.SkuFamily.A,
                    name=keyvault.SkuName.STANDARD,
                ),
                soft_delete_retention_in_days=90,
                network_acls=self._vault_network_rules(),
            ),
            opts=ResourceOptions(parent=self),
        )

    def _vault_network_rules(self) -> keyvault.NetworkRuleSetArgs | None:
        if self.config.public_network_access == keyvault.PublicNetworkAccess.ENABLED:
            return keyvault.NetworkRuleSetArgs(
                bypass="AzureServices",
                default_action=keyvault.NetworkRuleAction.DENY,
                ip_rules=[
                    keyvault.IPRuleArgs(value=str(ip)) for ip in self.config.allowed_public_networks
                ]
                if self.config.allowed_public_networks
                else [],
                virtual_network_rules=(
                    [
                        keyvault.VirtualNetworkRuleArgs(id=subnet_id)
                        for subnet_id in self.config.allowed_private_subnets
                    ]
                )
                if self.config.allowed_private_subnets
                else [],
            )
        return None

    def _diagnostic_settings(self) -> insights.DiagnosticSetting | None:
        if self.config.log_workspace_id:
            return diagnostic_setting(
                resource=self.vault,
                log_workspace_id=self.config.log_workspace_id,
                metric_categories=["AllMetrics"],
                log_categories=[
                    "AuditEvent",
                    "AzurePolicyEvaluationDetails",
                ],
                opts=pulumi.ResourceOptions(parent=self.vault),
            )

    def _outputs(self) -> None:
        self.register_outputs({"vault": self.vault})
        pulumi.export("keyvault_name", value=self.vault.name)
        pulumi.export("keyvault_id", value=self.vault.id)

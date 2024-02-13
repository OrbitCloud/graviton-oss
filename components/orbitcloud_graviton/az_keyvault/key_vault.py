from typing import List, Optional

import pulumi
from pulumi import ComponentResource, ResourceOptions
from pulumi_azure_native import keyvault
from pydantic import BaseModel, ConfigDict, model_validator

from orbitcloud_graviton.az_lib.types import AzureIdRef
from orbitcloud_graviton.az_network.types import PublicIPv4Network
from orbitcloud_graviton.pulumi_lib import AzureBase


class KeyVaultConfig(BaseModel):
    public_network_access: keyvault.PublicNetworkAccess = keyvault.PublicNetworkAccess.DISABLED
    allowed_private_vnets: Optional[List[AzureIdRef]] = None
    allowed_public_networks: Optional[List[PublicIPv4Network]] = None
    allow_azure_services: Optional[bool] = True

    @model_validator(mode="after")
    def validate_network_access(m: "KeyVaultConfig") -> "KeyVaultConfig":
        if m.public_network_access == keyvault.PublicNetworkAccess.ENABLED:
            if m.allowed_private_vnets is None and m.allowed_public_networks is None:
                pulumi.warn(
                    msg="KeyVault is configured to allow public network access, \
                        but no private subnets or public networks are allowed \
                        and default action is set to deny."
                )
        return m

    model_config = ConfigDict(arbitrary_types_allowed=True)


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

    def _vault(self) -> keyvault.Vault:
        return keyvault.Vault(
            resource_name=self.stack.name_for(resource_type=keyvault.Vault),
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
                        keyvault.VirtualNetworkRuleArgs(id=vnet)
                        for vnet in self.config.allowed_private_vnets
                    ]
                )
                if self.config.allowed_private_vnets
                else [],
            )
        return None

    def _outputs(self) -> None:
        self.register_outputs({"vault": self.vault})
        pulumi.export("keyvault_name", value=self.vault.name)
        pulumi.export("keyvault_id", value=self.vault.id)

from typing import Optional

import pulumi
from pulumi_azure_native import keyvault
from pydantic import BaseModel

from orbitcloud_graviton.pulumi_lib import AzureBase


class KeyVaultConfig(BaseModel):
    public_network_access: keyvault.PublicNetworkAccess = keyvault.PublicNetworkAccess.DISABLED


def key_vault(
    stack: AzureBase,
    config: KeyVaultConfig,
    opts: Optional[pulumi.ResourceOptions] = None,
) -> keyvault.Vault:
    vault = keyvault.Vault(
        resource_name=stack.name_for(keyvault.Vault),
        # vault_name=stack.name_for(keyvault.Vault),
        resource_group_name=stack.resource_group.name,
        location=stack.location,
        properties=keyvault.VaultPropertiesArgs(
            public_network_access=config.public_network_access,
            enable_rbac_authorization=True,
            tenant_id=str(stack.tenant_id),
            sku=keyvault.SkuArgs(
                family=keyvault.SkuFamily.A,
                name=keyvault.SkuName.STANDARD,
            ),
            soft_delete_retention_in_days=90,
        ),
        opts=opts,
    )

    return vault

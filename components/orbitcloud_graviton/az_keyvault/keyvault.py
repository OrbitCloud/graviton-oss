from importlib import resources
from typing import Dict, Optional

import pulumi
from orbitcloud_graviton.az_lib.naming import resource_namer
from pulumi_azure_native import keyvault, resources


# TODO:
# - implement properties:
# https://www.pulumi.com/registry/packages/azure-native/api-docs/keyvault/vault/#vaultproperties
#   - public_network_access
#   - Azure RBAC
#   - access policies
#   - enable soft delete
#   - purge protection
def az_keyvault(
    workload_name: str,
    env: str,
    location: str,
    resource_group: resources.ResourceGroup,
    tenant_id: str,
    tags: Optional[Dict[str, str]] = None,
    opts: Optional[pulumi.ResourceOptions] = None,
) -> keyvault.Vault:
    vault_name = resource_namer(
        workload_name=workload_name,
        env=env,
        location=location,
        resource_type=keyvault.Vault,
    )

    vault = keyvault.Vault(
        resource_name=vault_name,
        resource_group_name=resource_group.name,
        location=location,
        properties=keyvault.VaultPropertiesArgs(
            tenant_id=tenant_id,
            sku=keyvault.SkuArgs(
                family=keyvault.SkuFamily.A,
                name=keyvault.SkuName.STANDARD,
            ),
            access_policies=[],
            soft_delete_retention_in_days=90,
        ),
    )

    return vault

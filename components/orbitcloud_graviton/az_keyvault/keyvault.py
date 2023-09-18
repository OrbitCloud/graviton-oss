from typing import Dict, Optional

import pulumi
from orbitcloud_graviton.az_lib.config import StackConfig
from orbitcloud_graviton.az_lib.naming import resource_namer
from pulumi_azure_native import authorization, keyvault, resources


# TODO:
# - implement properties:
# https://www.pulumi.com/registry/packages/azure-native/api-docs/keyvault/vault/#vaultproperties
#   - public_network_access
#   - Azure RBAC
#   - access policies
#   - purge protection
def az_keyvault(
    workload_name: str,
    env: str,
    location: str,
    resource_group: resources.ResourceGroup | resources.AwaitableGetResourceGroupResult,
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
        tags=tags,
        opts=opts,
    )

    return vault


def az_keyvault_from_config(
    resource_group: resources.ResourceGroup | resources.AwaitableGetResourceGroupResult,
    config: StackConfig,
) -> keyvault.Vault:
    provider_client: authorization.GetClientConfigResult = (
        authorization.get_client_config()
    )

    return az_keyvault(
        workload_name=config.workload_name,
        env=config.env,
        location=config.location,
        resource_group=resource_group,
        tenant_id=provider_client.tenant_id,
    )

from typing import Optional

import pulumi
from pulumi_azure_native import containerregistry, keyvault

from orbitcloud_graviton.az_acr.registry import (
    ContainerRegistryConfig,
    container_registry,
)
from orbitcloud_graviton.az_keyvault import KeyVaultConfig, key_vault
from orbitcloud_graviton.entra_app import deployment_oidc_app
from orbitcloud_graviton.pulumi_lib import EntraBase, PulumiConfig, get_azure_stack, print_pulumi_esc_oidc_yaml


class LandingZoneConfig(PulumiConfig):
    containerregistry: Optional[ContainerRegistryConfig] = ContainerRegistryConfig()
    keyvault: Optional[KeyVaultConfig] = KeyVaultConfig()

    has_keyvault: Optional[bool] = True
    has_containerregistry: Optional[bool] = True


def deploy_landing_zone() -> None:
    config: LandingZoneConfig = LandingZoneConfig.model_validate({})
    entra_config = EntraBase.model_validate({})

    print(config)

    # Get Azure Stack and export resource group
    stack = get_azure_stack()

    pulumi.export("resource_group_id", stack.resource_group.id)
    pulumi.export("resource_group_name", stack.resource_group.name)

    # Container Registry
    if config.has_containerregistry and config.containerregistry:
        az_cr: containerregistry.Registry = container_registry(
            stack=stack,
            config=config.containerregistry,
            opts=pulumi.ResourceOptions(parent=stack.resource_group),
        )
        pulumi.export("containerregistry_server", az_cr.login_server)
        pulumi.export("containerregistry_id", az_cr.id)

    # Key Vault
    if config.has_keyvault and config.keyvault:
        az_kv: keyvault.Vault = key_vault(
            stack=stack,
            config=config.keyvault,
            opts=pulumi.ResourceOptions(parent=stack.resource_group),
        )
        pulumi.export("keyvault_name", az_kv.name)
        pulumi.export("keyvault_id", az_kv.id)

    # Pulumi Deployments Entra App - OIDC
    esc_app, _, _ = deployment_oidc_app(
        workload_name=stack.workload_name,
        pulumi_org=pulumi.get_organization(),
        subscription_id=str(stack.subscription_id),
        env=stack.env,
    )
    pulumi.Output.all(esc_app.client_id, entra_config.tenant_id, stack.subscription_id).apply(
        func=print_pulumi_esc_oidc_yaml
    )

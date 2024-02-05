from typing import Optional

import pulumi
from pulumi_azure_native import containerregistry, keyvault

from orbitcloud_graviton.az_acr.registry import (
    ContainerRegistryConfig,
    container_registry,
)
from orbitcloud_graviton.az_eventhub import EventHub, NamespaceConfig
from orbitcloud_graviton.az_keyvault import KeyVaultConfig, key_vault
from orbitcloud_graviton.entra import (
    AzureRbacPermission,
    EntraApp,
    EntraAppConfig,
    GitHubOIDCCredentials,
    PulumiOIDCCredentials,
)
from orbitcloud_graviton.pulumi_lib import (
    EntraBase,
    PulumiConfig,
    get_azure_stack,
    print_pulumi_esc_oidc_yaml,
)


class LandingZoneConfig(PulumiConfig):
    container_registry: Optional[ContainerRegistryConfig] = ContainerRegistryConfig()
    keyvault: Optional[KeyVaultConfig] = KeyVaultConfig()
    eventhub: Optional[NamespaceConfig]

    has_keyvault: Optional[bool] = True
    has_containerregistry: Optional[bool] = True

    github_cr_app: Optional[GitHubOIDCCredentials] = None


def deploy_landing_zone() -> None:
    config: LandingZoneConfig = LandingZoneConfig.model_validate({})
    entra_config = EntraBase.model_validate({})

    # Get Azure Stack and export resource group
    stack = get_azure_stack()

    #
    #   Container Registry
    #
    if config.has_containerregistry and config.container_registry:
        az_cr: containerregistry.Registry = container_registry(
            stack=stack,
            config=config.container_registry,
            opts=pulumi.ResourceOptions(parent=stack.resource_group),
        )
        pulumi.export("containerregistry_server", az_cr.login_server)
        pulumi.export("containerregistry_id", az_cr.id)

    #
    #   Key Vault
    #
    if config.has_keyvault and config.keyvault:
        az_kv: keyvault.Vault = key_vault(
            stack=stack,
            config=config.keyvault,
            opts=pulumi.ResourceOptions(parent=stack.resource_group),
        )
        pulumi.export("keyvault_name", az_kv.name)
        pulumi.export("keyvault_id", az_kv.id)

    #
    #   Event Hub
    #
    if config.eventhub:
        # Event Hub
        EventHub(
            stack=stack,
            config=config.eventhub,
            opts=pulumi.ResourceOptions(parent=stack.resource_group),
        )

    #
    #   Entra App for Pulumi deployments
    #
    entra_pulumi_app = EntraApp(
        stack=stack,
        entra=entra_config,
        config=EntraAppConfig(
            name=f"pulumi-deployments-{stack.workload_name}-{stack.env}",
            federated_credentials=PulumiOIDCCredentials(
                organization=pulumi.get_organization()
            ).credentials(),
            azure_permissions=[
                AzureRbacPermission(
                    role_name="Contributor",
                    scope=f"/subscriptions/{stack.subscription_id}",
                )
            ],
        ),
    )

    pulumi.Output.all(
        entra_pulumi_app.app.client_id, entra_config.tenant_id, stack.subscription_id
    ).apply(func=print_pulumi_esc_oidc_yaml)

    #
    #   Entra App for GitHub Container Registry
    #
    if config.github_cr_app:
        entra_app_github = EntraApp(
            stack=stack,
            entra=entra_config,
            config=EntraAppConfig(
                name=f"github-cr-{stack.workload_name}-{stack.env}",
                federated_credentials=config.github_cr_app.credentials(),
            ),
        )
        pulumi.export("github_cr_app_client_id", entra_app_github.app.client_id)
        pulumi.export("github_cr_app_tenant_id", entra_config.tenant_id)
        pulumi.export("github_cr_app_subscription_id", stack.subscription_id)

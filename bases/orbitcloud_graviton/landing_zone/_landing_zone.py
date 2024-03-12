from typing import Optional

import pulumi
from pulumi_azure_native import operationalinsights

from orbitcloud_graviton.acme_ssl.acme import AcmeSsl, AcmeSslConfig
from orbitcloud_graviton.az_acr import (
    ContainerRegistryConfig,
    container_registry,
)
from orbitcloud_graviton.az_eventhub import EventHub, NamespaceConfig
from orbitcloud_graviton.az_iam import IamAssignmentConfig, iam_assignment
from orbitcloud_graviton.az_keyvault import KeyVault, KeyVaultConfig
from orbitcloud_graviton.az_monitor import LogWorkspaceConfig, log_workspace
from orbitcloud_graviton.az_network.dns_zone import DnsZone, DnsZoneConfig
from orbitcloud_graviton.az_providerhub import provider_registration
from orbitcloud_graviton.entra import (
    EntraApp,
    EntraAppConfig,
    GitHubOIDCCredentials,
    PulumiOIDCCredentials,
)
from orbitcloud_graviton.pulumi_lib import (
    AzureBase,
    EntraBase,
    PulumiConfig,
    generate_stack_schema,
    get_azure_stack,
    get_entra_stack,
    print_pulumi_esc_oidc_yaml,
)


class LandingZoneConfig(PulumiConfig):
    container_registry: Optional[ContainerRegistryConfig] = ContainerRegistryConfig()
    keyvault: Optional[KeyVaultConfig] = KeyVaultConfig()
    eventhub: Optional[NamespaceConfig] = None
    log_workspace: LogWorkspaceConfig = LogWorkspaceConfig()

    has_keyvault: Optional[bool] = True
    has_container_registry: Optional[bool] = True

    pulumi_app_additional_permissions: Optional[list[IamAssignmentConfig]] = None

    github_cr_app: Optional[GitHubOIDCCredentials] = None
    resource_providers: Optional[list[str]] = None

    dns_zone: Optional[DnsZoneConfig] = None
    acme_ssl: Optional[bool] = False


def deploy_landing_zone() -> None:
    generate_stack_schema(model=LandingZoneConfig, output_file=".stack_schema.json")
    config: LandingZoneConfig = LandingZoneConfig.model_validate({})
    entra_config: EntraBase = EntraBase.model_validate({})

    # Get Azure Stack and export resource group
    stack: AzureBase = get_azure_stack()
    entra: EntraBase = get_entra_stack()

    ##########################################
    # Log Workspace
    ##########################################
    logs: operationalinsights.Workspace = log_workspace(
        config=config.log_workspace,
        stack=stack,
        opts=pulumi.ResourceOptions(parent=stack.resource_group),
    )

    ##########################################
    #   Key Vault
    ##########################################
    if config.has_keyvault and config.keyvault:
        kv = KeyVault(
            stack=stack,
            config=config.keyvault.model_copy(update={"log_workspace_id": logs.id}),
            opts=pulumi.ResourceOptions(parent=stack.resource_group),
        )

    ##########################################
    #   Dns Zone
    ##########################################
    if config.dns_zone:
        dns = DnsZone(
            stack=stack,
            config=config.dns_zone,
            opts=pulumi.ResourceOptions(parent=stack.resource_group),
        )

        if config.acme_ssl:
            AcmeSsl(
                stack=stack,
                entra_config=entra,
                config=AcmeSslConfig(
                    dns_zone_id=dns.zone.id,
                    dns_zone_name=config.dns_zone.name,
                    keyvault_id=kv.vault.id,
                    acme_account_email="admin@orbit.is",
                ),
            )

    ##########################################
    #   Container Registry
    ##########################################
    if config.has_container_registry and config.container_registry:
        container_registry(
            stack=stack,
            config=config.container_registry,
            opts=pulumi.ResourceOptions(parent=stack.resource_group),
        )

    ##########################################
    #   Event Hub
    ##########################################
    if config.eventhub:
        # Event Hub
        EventHub(
            stack=stack,
            config=config.eventhub.model_copy(update={"log_workspace_id": logs.id}),
            opts=pulumi.ResourceOptions(parent=stack.resource_group),
        )

    ##########################################
    #   Entra App for Pulumi deployments
    ##########################################

    pulumi_app = EntraApp(
        stack=stack.model_copy(update={"exports_prefix": "pulumi"}),
        entra=entra_config,
        config=EntraAppConfig(
            name="pulumi-deployments",
            federated_credentials=PulumiOIDCCredentials(
                organization=pulumi.get_organization()
            ).credentials(),
        ),
    )

    pulumi_app_permissions: list[IamAssignmentConfig] = [
        IamAssignmentConfig(
            name_prefix="lz",
            role="Contributor",
            scope=f"/subscriptions/{stack.subscription_id}",
            description="Allows Pulumi to deploy resources in the subscription",
        ),
        IamAssignmentConfig(
            name_prefix="lz",
            role="Role Based Access Control Administrator",
            scope=f"/subscriptions/{stack.subscription_id}",
            description="Allows Pulumi to assign roles to resources in the subscription",
        ),
        IamAssignmentConfig(
            name_prefix="lz",
            role="Key Vault Secrets Officer",
            scope=f"/subscriptions/{stack.subscription_id}",
            description="Allows Pulumi to read and write secrets in Key Vault",
        ),
    ]
    if config.pulumi_app_additional_permissions:
        pulumi_app_permissions.extend(config.pulumi_app_additional_permissions)

    for permission in pulumi_app_permissions:
        iam_assignment(
            stack=stack,
            config=permission,
            principal=pulumi_app.service_principal,
            opts=pulumi.ResourceOptions(
                parent=pulumi_app.service_principal, delete_before_replace=True
            ),
        )

    pulumi.Output.all(
        pulumi_app.app.client_id, entra_config.tenant_id, stack.subscription_id
    ).apply(func=print_pulumi_esc_oidc_yaml)

    ##########################################
    #   Entra App for GitHub Container Registry
    ##########################################
    if config.github_cr_app:
        EntraApp(
            stack=stack.model_copy(update={"exports_prefix": "github"}),
            entra=entra_config,
            config=EntraAppConfig(
                name=f"github-cr-{stack.workload_name}-{stack.env}",
                federated_credentials=config.github_cr_app.credentials(),
            ),
        )

    if config.resource_providers:
        for provider in config.resource_providers:
            provider_registration(
                stack=stack,
                provider_namespace=provider,
                opts=pulumi.ResourceOptions(parent=stack.resource_group),
            )

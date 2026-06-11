import pulumi
from pulumi_azure_native import operationalinsights

from orbitcloud_graviton.acme_ssl.acme import AcmeSsl, AcmeSslConfig
from orbitcloud_graviton.az_acr import (
    ContainerRegistryConfig,
    container_registry,
)
from orbitcloud_graviton.az_ai import SearchService, SearchServiceConfig
from orbitcloud_graviton.az_eventgrid import EventGridDomain, EventGridDomainConfig
from orbitcloud_graviton.az_eventhub import EventHub, NamespaceConfig
from orbitcloud_graviton.az_iam import iam_assignment
from orbitcloud_graviton.az_keyvault import KeyVault, KeyVaultConfig
from orbitcloud_graviton.az_monitor import LogWorkspaceConfig, log_workspace
from orbitcloud_graviton.az_network.dns_zone import DnsZone, DnsZoneConfig
from orbitcloud_graviton.entra import (
    EntraApp,
    EntraAppAuthentication,
    EntraAppBranding,
    EntraAppConfig,
)
from orbitcloud_graviton.entra.oidc_providers import WorkloadIdentityConfig
from orbitcloud_graviton.pulumi_lib import (
    AzureStack,
    EntraStack,
    PulumiConfig,
    get_azure_stack,
)
from orbitcloud_graviton.pulumi_lib.stack_schema import generate_stack_schema


class LandingZoneConfig(PulumiConfig):
    container_registry: ContainerRegistryConfig | None = ContainerRegistryConfig()
    keyvault: KeyVaultConfig | None = KeyVaultConfig()
    eventhub: NamespaceConfig | None = None
    eventgrid_domain: EventGridDomainConfig | None = None
    log_workspace: LogWorkspaceConfig = LogWorkspaceConfig()

    has_keyvault: bool | None = True
    has_container_registry: bool | None = True

    search_service: SearchServiceConfig | None = None

    workload_identities: list[WorkloadIdentityConfig] | None = None
    resource_providers: list[str] | None = None

    dns_zone: DnsZoneConfig | None = None
    acme_ssl: bool | None = False


def deploy_landing_zone() -> None:
    generate_stack_schema(model=LandingZoneConfig, output_file=".stack_schema.json")
    config: LandingZoneConfig = LandingZoneConfig.model_validate({})
    entra_config: EntraStack = EntraStack.model_validate({})

    # Get Azure Stack and export resource group
    stack: AzureStack = get_azure_stack()

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
        DnsZone(
            stack=stack,
            config=config.dns_zone,
            opts=pulumi.ResourceOptions(parent=stack.resource_group),
        )

        if config.acme_ssl:
            AcmeSsl(
                stack=stack,
                config=AcmeSslConfig(
                    dns_zone_name=config.dns_zone.name,
                    keyvault_id=kv.vault.id if kv else None,
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
    #   Event Grid Domain
    ##########################################
    if config.eventgrid_domain:
        # Event Hub
        EventGridDomain(
            stack=stack,
            config=config.eventgrid_domain.model_copy(update={"log_workspace_id": logs.id}),
            opts=pulumi.ResourceOptions(parent=stack.resource_group),
        )

    ##########################################
    #   Search Service
    ##########################################
    if config.search_service:
        SearchService(
            stack=stack,
            config=config.search_service.model_copy(update={"log_workspace_id": logs.id}),
            opts=pulumi.ResourceOptions(parent=stack.resource_group),
        )

    ##########################################
    # Entra Apps for VCS credentials
    ##########################################
    if config.workload_identities:
        for cred in config.workload_identities:
            entra_app = EntraApp(
                stack=stack.model_copy(update={"exports_prefix": cred.workload.credential_type}),
                entra=entra_config,
                config=EntraAppConfig(
                    name=f"{cred.workload.credential_type}",
                    federated_credentials=cred.workload.credentials(),
                    authentication=EntraAppAuthentication(
                        branding=EntraAppBranding(internal_notes=cred.internal_notes)
                    ),
                ),
            )

            for permission in cred.azure_permissions or []:
                iam_assignment(
                    stack=stack,
                    config=permission,
                    principal_id=entra_app.service_principal.object_id,
                    opts=pulumi.ResourceOptions(
                        parent=entra_app.service_principal, delete_before_replace=True
                    ),
                )

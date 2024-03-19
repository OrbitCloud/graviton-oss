from typing import List, Optional

import pulumi
from pulumi_azure_native import insights, operationalinsights
from pydantic import Field

from orbitcloud_graviton.az_acr.registry import ContainerRegistryConfig, container_registry
from orbitcloud_graviton.az_app import ContainerAppEnv, ContainerAppEnvConfig
from orbitcloud_graviton.az_eventhub import EventHub, NamespaceConfig
from orbitcloud_graviton.az_iam.assignment import iam_assignment
from orbitcloud_graviton.az_keyvault import KeyVault, KeyVaultConfig
from orbitcloud_graviton.az_monitor import (
    AppInsightsConfig,
    LogWorkspaceConfig,
    app_insights,
    log_workspace,
)
from orbitcloud_graviton.az_storage import StorageAccountConfig, storage_account
from orbitcloud_graviton.entra.entra_app import EntraApp, EntraAppConfig
from orbitcloud_graviton.entra.oidc_providers import WorkloadIdentityConfig
from orbitcloud_graviton.pulumi_lib import AzureBase, PulumiConfig, get_azure_stack
from orbitcloud_graviton.pulumi_lib.azure_base import EntraBase, get_entra_stack
from orbitcloud_graviton.pulumi_lib.stack_schema import generate_stack_schema


class AppZoneBaseConfig(PulumiConfig):
    containerapp_env: ContainerAppEnvConfig = Field(
        default=ContainerAppEnvConfig(), title="Container App Environment Configuration"
    )
    log_workspace: LogWorkspaceConfig = LogWorkspaceConfig()
    keyvault: KeyVaultConfig = Field(
        default=KeyVaultConfig(), title="Key Vault Config", description="Key Vault Configuration"
    )
    event_hub: Optional[NamespaceConfig] = None

    has_container_registry: Optional[bool] = False
    container_registry: Optional[ContainerRegistryConfig] = ContainerRegistryConfig()

    app_insights: Optional[AppInsightsConfig] = None
    storage_accounts: Optional[List[StorageAccountConfig]] = None

    workload_identities: Optional[List[WorkloadIdentityConfig]] = None


def deploy() -> None:
    generate_stack_schema(model=AppZoneBaseConfig, output_file=".stack_schema.json")
    config: AppZoneBaseConfig = AppZoneBaseConfig.model_validate({})

    stack: AzureBase = get_azure_stack()
    entra_config: EntraBase = get_entra_stack()

    ##########################################
    # Log Workspace
    ##########################################
    logs: operationalinsights.Workspace = log_workspace(
        config=config.log_workspace,
        stack=stack,
        opts=pulumi.ResourceOptions(parent=stack.resource_group),
    )

    ##########################################
    # Application Insights
    ##########################################
    appi: insights.Component = app_insights(
        stack=stack,
        config=AppInsightsConfig(log_workspace_id=logs.id).model_copy(
            update=config.app_insights.model_dump() if config.app_insights else {}
        ),
        opts=pulumi.ResourceOptions(parent=stack.resource_group),
    )

    ##########################################
    # Container App Environment
    ##########################################
    ContainerAppEnv(
        stack=stack,
        config=config.containerapp_env.model_copy(
            update={
                "log_workspace_id": logs.id,
                "dapr_appi_connstring": appi.connection_string,
                "dapr_appi_instrumentation_key": appi.instrumentation_key,
            },
        ),
        opts=pulumi.ResourceOptions(parent=stack.resource_group),
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
    # Key Vault
    ##########################################
    KeyVault(
        stack=stack,
        config=config.keyvault.model_copy(
            update={"log_workspace_id": logs.id},
        ),
        opts=pulumi.ResourceOptions(parent=stack.resource_group),
    )

    ##########################################
    # Event Hub
    ##########################################
    if config.event_hub:
        EventHub(
            stack=stack,
            config=config.event_hub.model_copy(
                update={"log_workspace_id": stack.resource_group.name}
            ),
            opts=pulumi.ResourceOptions(parent=stack.resource_group),
        )

    ##########################################
    # Storage Account
    ##########################################
    for st in config.storage_accounts or []:
        storage_account.StorageAccount(
            stack=stack,
            config=st.model_copy(
                update={"log_workspace_id": logs.id},
            ),
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
                ),
            )

            for permission in cred.azure_permissions or []:
                iam_assignment(
                    stack=stack,
                    config=permission,
                    principal_id=entra_app.service_principal.id,
                    opts=pulumi.ResourceOptions(
                        parent=entra_app.service_principal, delete_before_replace=True
                    ),
                )

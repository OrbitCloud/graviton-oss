from typing import Optional

import pulumi
from pulumi_azure_native import operationalinsights
from pydantic import Field

from orbitcloud_graviton.az_acr.registry import ContainerRegistryConfig
from orbitcloud_graviton.az_app import ContainerAppEnv, ContainerAppEnvConfig
from orbitcloud_graviton.az_eventhub import EventHub, NamespaceConfig
from orbitcloud_graviton.az_keyvault import KeyVault, KeyVaultConfig
from orbitcloud_graviton.az_monitor import LogWorkspaceConfig, log_workspace
from orbitcloud_graviton.az_storage import StorageAccountConfig
from orbitcloud_graviton.pulumi_lib import AzureBase, PulumiConfig, get_azure_stack


class AppHubBaseConfig(PulumiConfig):
    containerapp_env: ContainerAppEnvConfig = Field(
        default=ContainerAppEnvConfig(), title="Container App Environment Configuration"
    )
    log_workspace: LogWorkspaceConfig = LogWorkspaceConfig()
    keyvault: KeyVaultConfig = Field(
        default=KeyVaultConfig(), title="Key Vault Config", description="Key Vault Configuration"
    )
    event_hub: Optional[NamespaceConfig] = None
    storage_account: Optional[StorageAccountConfig] = None
    container_registry: Optional[ContainerRegistryConfig] = None


def deploy() -> None:
    config: AppHubBaseConfig = AppHubBaseConfig.model_validate({})

    stack: AzureBase = get_azure_stack()

    ##########################################
    # Log Workspace
    ##########################################
    logs: operationalinsights.Workspace = log_workspace(
        config=config.log_workspace,
        stack=stack,
        opts=pulumi.ResourceOptions(parent=stack.resource_group),
    )

    ##########################################
    # Container App Environment
    ##########################################
    ContainerAppEnv(
        stack=stack,
        config=config.containerapp_env.model_copy(
            update={"log_workspace_id": logs.id},
        ),
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

from inspect import cleandoc
from typing import List, Optional, Union

import pulumi
from pulumi_azure_native.resources import ResourceGroup
from pydantic import model_validator

from orbitcloud_graviton.az_ai.search_service import SearchService, SearchServiceConfig
from orbitcloud_graviton.az_app.container_app import ContainerApp, ContainerAppConfig
from orbitcloud_graviton.az_appconfig import AppConfiguration, AppConfigurationConfig
from orbitcloud_graviton.az_iam.assignment import IamAssignmentConfig
from orbitcloud_graviton.az_storage import StorageAccount, StorageAccountConfig
from orbitcloud_graviton.pulumi_lib import (
    AzureStack,
    PulumiConfig,
    generate_stack_schema,
    get_azure_stack,
)


class AppWorkloadConfig(PulumiConfig):
    apps: List[ContainerAppConfig]
    app_config: Optional[AppConfigurationConfig] = None
    storage_accounts: Optional[List[StorageAccountConfig]] = None
    search_service: Optional[SearchServiceConfig] = None

    @model_validator(mode="after")
    def validate_apps(m: "AppWorkloadConfig") -> "AppWorkloadConfig":
        # If more than one app, ensure unique names
        # names are either derived from the workload_name or explicitly set

        if len(m.apps) > 1:
            app_names: List[str | None] = [app.name for app in m.apps]
            if len(app_names) != len(set(app_names)):
                raise ValueError(
                    cleandoc(
                        doc="""
                        Multiple apps found in configuration, which will end up having colliding names.
                        Ensure that no more than one app within the stack doesn't have the name parameter
                        explicitly set (by default it will be derived from the workload name)."
                        """
                    )
                )

        return m


def deploy() -> None:
    generate_stack_schema(model=AppWorkloadConfig, output_file=".stack_schema.json")
    config: AppWorkloadConfig = AppWorkloadConfig.model_validate({})
    stack: AzureStack = get_azure_stack()

    rg: ResourceGroup = stack.resource_group
    opts = pulumi.ResourceOptions(parent=rg)

    # Secrets from dependencies to register in Container App
    app_secrets: dict[str, Union[str, pulumi.Output[str] | None]] = {}
    app_perms: List[IamAssignmentConfig] = []

    ##########################################
    # App Configuration Store
    ##########################################
    if config.app_config:
        appcs: AppConfiguration = AppConfiguration(
            stack=stack,
            config=config.app_config,
        )
        app_secrets["appconfig-endpoint"] = appcs.app_config.endpoint
        app_perms.extend(
            [
                IamAssignmentConfig(
                    role="App Configuration Data Reader",
                    scope=appcs.app_config.id,
                ),
                IamAssignmentConfig(
                    role="Reader",
                    scope=appcs.app_config.id,
                ),
            ]
        )

    ##########################################
    # Storage Accounts
    ##########################################
    for st in config.storage_accounts or []:
        _st = StorageAccount(
            stack=stack.model_copy(update={"exports_prefix": st.name}),
            config=st,
            opts=opts,
        )
        app_secrets.update(_st.get_endpoints(suffix="endpoint"))

        if st.app_permissions:
            app_perms.extend(
                [
                    IamAssignmentConfig(
                        role=role,
                        scope=_st.storage_account.id,
                    )
                    for role in st.app_permissions.roles()
                ]
            )

    ##########################################
    # Search Service
    ##########################################
    if config.search_service:
        SearchService(
            stack=stack,
            config=config.search_service,
            opts=opts,
        )

    ##########################################
    # App Configuration Store
    ##########################################
    for container_app in config.apps:
        if container_app.secrets:
            app_secrets.update(container_app.secrets)

        perms: List[IamAssignmentConfig] = container_app.azure_permissions or []
        perms.extend(app_perms)

        ContainerApp(
            stack=stack,
            config=container_app.model_copy(
                update={"secrets": app_secrets, "azure_permissions": perms}
            ),
            opts=opts,
        )

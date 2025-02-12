from inspect import cleandoc

import pulumi
from pulumi_azure_native.resources import ResourceGroup
from pydantic import model_validator

from orbitcloud_graviton.az_ai import SearchService, SearchServiceConfig
from orbitcloud_graviton.az_app import (
    ContainerApp,
    ContainerAppConfig,
    ContainerAppJobConfig,
)
from orbitcloud_graviton.az_app.secrets import InlineSecret, Secret
from orbitcloud_graviton.az_appconfig import AppConfiguration, AppConfigurationConfig
from orbitcloud_graviton.az_iam import IamAssignmentConfig
from orbitcloud_graviton.az_storage import StorageAccount, StorageAccountConfig
from orbitcloud_graviton.entra import EntraApp, EntraAppConfig
from orbitcloud_graviton.pulumi_lib import (
    AzureStack,
    EntraStack,
    PulumiConfig,
    generate_stack_schema,
    get_azure_stack,
    get_entra_stack,
)


class AppWorkloadConfig(PulumiConfig):
    apps: list[ContainerAppConfig] | None = None
    jobs: list[ContainerAppJobConfig] | None = None
    app_config: AppConfigurationConfig | None = None
    storage_accounts: list[StorageAccountConfig] | None = None
    search_service: SearchServiceConfig | None = None
    oauth_app: EntraAppConfig | None = None

    @model_validator(mode="after")
    def validate_apps(m: "AppWorkloadConfig") -> "AppWorkloadConfig":
        # If more than one app, ensure unique names
        # names are either derived from the workload_name or explicitly set

        if m.apps and len(m.apps) > 1:
            app_names: list[str | None] = [app.name for app in m.apps]
            if len(app_names) != len(set(app_names)):
                raise ValueError(
                    cleandoc(
                        doc="""
                        When more than one app is defined, app names must be unique.
                        Only one app can be defined without a name and other apps need to have
                        unique names.
                        """
                    )
                )

        return m


def deploy() -> None:
    generate_stack_schema(model=AppWorkloadConfig, output_file=".stack_schema.json")
    config: AppWorkloadConfig = AppWorkloadConfig.model_validate({})
    stack: AzureStack = get_azure_stack()
    entra_config: EntraStack = get_entra_stack()

    rg: ResourceGroup = stack.resource_group
    opts = pulumi.ResourceOptions(parent=rg)

    # Secrets from dependencies to register in Container App
    app_secrets: list[Secret] = []
    app_perms: list[IamAssignmentConfig] = []
    app_deps = []

    ##########################################
    # Storage Accounts
    ##########################################
    for st in config.storage_accounts or []:
        _st = StorageAccount(
            stack=stack.model_copy(update={"exports_prefix": st.name}),
            config=st,
            opts=opts,
        )
        app_secrets.extend(
            [
                InlineSecret(key=key, value=val)
                for key, val in _st.get_endpoints(suffix="endpoint").items()
            ]
        )

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

        app_deps.append(_st)

    ##########################################
    # Search Service
    ##########################################
    if config.search_service:
        search = SearchService(
            stack=stack,
            config=config.search_service,
            opts=opts,
        )

        app_deps.append(search)

    ##########################################
    # App Configuration Store
    ##########################################
    if config.app_config:
        appcs: AppConfiguration = AppConfiguration(
            stack=stack,
            config=config.app_config,
            opts=pulumi.ResourceOptions.merge(opts, pulumi.ResourceOptions(depends_on=app_deps)),
        )
        app_secrets.append(
            InlineSecret(
                key="appconfig-endpoint",
                value=appcs.app_config.endpoint,
            )
        )

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
        app_deps.append(appcs)

    ##########################################
    # Container Apps
    ##########################################
    for container_app in config.apps or []:
        if container_app.secrets:
            app_secrets.extend(container_app.secrets)

        perms: list[IamAssignmentConfig] = container_app.azure_permissions or []
        perms.extend(app_perms)

        ContainerApp(
            stack=stack,
            config=container_app.model_copy(
                update={"secrets": app_secrets, "azure_permissions": perms}
            ),
            opts=pulumi.ResourceOptions.merge(opts, pulumi.ResourceOptions(depends_on=app_deps)),
        )

    ##########################################
    # Container App Jobs
    ##########################################

    for job in config.jobs or []:
        if job.secrets:
            app_secrets.extend(job.secrets)

        perms: list[IamAssignmentConfig] = job.azure_permissions or []
        perms.extend(app_perms)

        ContainerApp(
            stack=stack,
            config=job.model_copy(update={"secrets": app_secrets, "azure_permissions": perms}),
            opts=pulumi.ResourceOptions.merge(opts, pulumi.ResourceOptions(depends_on=app_deps)),
        )

    if config.oauth_app:
        EntraApp(
            stack=stack.model_copy(update={"exports_prefix": "oauth"}),
            entra=entra_config,
            config=config.oauth_app,
        )

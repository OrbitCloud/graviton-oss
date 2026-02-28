from inspect import cleandoc

import pulumi
from pulumi_azure_native.resources import ResourceGroup
from pydantic import model_validator

from orbitcloud_graviton.az_ai import SearchService, SearchServiceConfig
from orbitcloud_graviton.az_app import (
    ContainerApp,
    ContainerAppConfig,
    ContainerAppJobConfig,
    HttpRouteConfigModel,
    build_http_route_config,
)
from orbitcloud_graviton.az_app.outputs import ContainerAppEnvOutput
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
    http_routes: list[HttpRouteConfigModel] | None = None

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

    @model_validator(mode="after")
    def validate_http_routes(m: "AppWorkloadConfig") -> "AppWorkloadConfig":
        if m.http_routes and len(m.http_routes) > 1:
            route_names = [route.name for route in m.http_routes]
            if len(route_names) != len(set(route_names)):
                raise ValueError("HTTP route config names must be unique.")
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
    container_app_resources: list[ContainerApp] = []
    for container_app in config.apps or []:
        if container_app.secrets:
            app_secrets.extend(container_app.secrets)

        perms: list[IamAssignmentConfig] = container_app.azure_permissions or []
        perms.extend(app_perms)

        ca = ContainerApp(
            stack=stack,
            config=container_app.model_copy(
                update={"secrets": app_secrets, "azure_permissions": perms}
            ),
            opts=pulumi.ResourceOptions.merge(opts, pulumi.ResourceOptions(depends_on=app_deps)),
        )
        container_app_resources.append(ca)

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

    ##########################################
    # HTTP Route Configs
    ##########################################
    if config.http_routes:
        # Resolve environment name and resource group from the first app's environment ref
        first_app = config.apps[0] if config.apps else None
        if first_app is None:
            raise ValueError(
                "http_routes requires at least one app to be defined "
                "(environment_output_ref is needed for route config)"
            )
        env_output = ContainerAppEnvOutput.model_validate(first_app.environment_output_ref)
        route_opts = pulumi.ResourceOptions.merge(
            opts, pulumi.ResourceOptions(depends_on=container_app_resources)
        )
        for route_config in config.http_routes:
            build_http_route_config(
                environment_name=env_output.name,
                resource_group_name=env_output.resource_group_name,
                config=route_config,
                opts=route_opts,
            )

    if config.oauth_app:
        EntraApp(
            stack=stack.model_copy(update={"exports_prefix": "oauth"}),
            entra=entra_config,
            config=config.oauth_app,
        )

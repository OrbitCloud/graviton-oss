from typing import List, Optional

import pulumi
from pulumi_azure_native.resources import ResourceGroup

from orbitcloud_graviton.az_app.container_app import ContainerApp, ContainerAppConfig
from orbitcloud_graviton.az_appconfig.app_config import AppConfiguration, AppConfigurationConfig
from orbitcloud_graviton.az_iam.assignment import IamAssignmentConfig, iam_assignment
from orbitcloud_graviton.pulumi_lib import (
    AzureBase,
    PulumiConfig,
    generate_stack_schema,
    get_azure_stack,
)
from orbitcloud_graviton.pulumi_lib.helpers import fmt_name


class AppWorkloadConfig(PulumiConfig):
    apps: List[ContainerAppConfig]
    app_config: Optional[AppConfigurationConfig] = None


def deploy() -> None:
    generate_stack_schema(model=AppWorkloadConfig, output_file=".stack_schema.json")
    config: AppWorkloadConfig = AppWorkloadConfig.model_validate({})
    stack: AzureBase = get_azure_stack()

    rg: ResourceGroup = stack.resource_group
    opts = pulumi.ResourceOptions(parent=rg)

    secrets: dict[str, str] = {}
    if config.app_config:
        app_config: AppConfiguration = AppConfiguration(
            stack=stack,
            config=config.app_config,
        )
        if config.app_config.export_endpoint_as_secret:
            secret_name = fmt_name(config.app_config.export_endpoint_as_secret)
            secrets[secret_name] = app_config.app_config.endpoint

    for ca_config in config.apps:
        if ca_config.secrets:
            secrets.update(ca_config.secrets)

        app = ContainerApp(
            stack=stack,
            config=ca_config.model_copy(update={"secrets": secrets}),
            opts=opts,
        )

        if app_config:
            iam_assignment(
                stack=stack,
                config=IamAssignmentConfig(
                    role="App Configuration Data Reader",
                    scope=app_config.app_config.id,
                ),
                principal_id=app.app.identity.apply(lambda x: x.principal_id),
            )

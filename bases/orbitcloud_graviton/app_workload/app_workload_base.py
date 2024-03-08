from typing import List

import pulumi
from pulumi_azure_native.resources import ResourceGroup

from orbitcloud_graviton.az_app.container_app import ContainerApp, ContainerAppConfig
from orbitcloud_graviton.pulumi_lib import (
    AzureBase,
    PulumiConfig,
    generate_stack_schema,
    get_azure_stack,
)


class AppWorkloadConfig(PulumiConfig):
    apps: List[ContainerAppConfig]  # noqa: F821


def deploy() -> None:
    generate_stack_schema(model=AppWorkloadConfig, output_file=".stack_schema.json")
    config: AppWorkloadConfig = AppWorkloadConfig.model_validate({})
    stack: AzureBase = get_azure_stack()

    rg: ResourceGroup = stack.resource_group
    opts = pulumi.ResourceOptions(parent=rg)

    for app_config in config.apps:
        ContainerApp(stack=stack, config=app_config, opts=opts)

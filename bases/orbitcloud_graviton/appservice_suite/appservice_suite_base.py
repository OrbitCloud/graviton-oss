from typing import Optional

import pulumi
from pulumi_azure_native import resources

from orbitcloud_graviton.az_appservice import (
    az_appservice_plan_from_config,
)
from orbitcloud_graviton.pulumi_lib import AzureBase, PulumiConfig, get_azure_stack


class AppserviceSuiteConfig(PulumiConfig):
    include_log_workspace: Optional[bool] = True
    log_workspace_ref_id: Optional[str] = None
    include_keyvault: Optional[bool] = True


def deploy() -> None:
    stack: AzureBase = get_azure_stack()
    config: AppserviceSuiteConfig = AppserviceSuiteConfig()

    # Resource Group
    az_rg: resources.ResourceGroup = stack.resource_group

    pulumi.export("resource_group_name", az_rg.name)

    # App Service Plan
    az_asp = az_appservice_plan_from_config(config=config, resource_group=az_rg)
    pulumi.export("appservice_plan_name", az_asp.name)

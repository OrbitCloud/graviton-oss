from dataclasses import dataclass
from typing import Optional

import pulumi
from pulumi_azure_native import resources

from orbitcloud_graviton.az_appservice import (
    AppServicePlanStackSchema,
    az_appservice_plan_from_config,
)
from orbitcloud_graviton.az_lib import Confy, StackConfig
from orbitcloud_graviton.az_resources import az_resource_group_from_config


@dataclass(kw_only=True, frozen=True)
class AppserviceSuiteConfig(StackConfig, AppServicePlanStackSchema):
    include_log_workspace: Optional[bool] = True
    log_workspace_ref_id: Optional[str] = None
    include_keyvault: Optional[bool] = True


def deploy() -> None:
    config: AppserviceSuiteConfig = Confy(AppserviceSuiteConfig).populate()

    # Resource Group
    az_rg: resources.ResourceGroup = az_resource_group_from_config(config=config)

    pulumi.export("resource_group_name", az_rg.name)

    # App Service Plan
    az_asp = az_appservice_plan_from_config(config=config, resource_group=az_rg)
    pulumi.export("appservice_plan_name", az_asp.name)

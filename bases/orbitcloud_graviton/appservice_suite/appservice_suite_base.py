import sys
from dataclasses import dataclass, fields
from typing import Optional

import pulumi
from orbitcloud_graviton.az_appservice import (
    AppServicePlanStackSchema,
    az_appservice_plan_from_config,
)
from orbitcloud_graviton.az_keyvault.keyvault import az_keyvault_from_config
from orbitcloud_graviton.az_lib import Confy, StackConfig
from orbitcloud_graviton.az_resources import az_resource_group_from_config
from pulumi_azure_native import resources


@dataclass(kw_only=True, frozen=True)
class AppserviceSuiteConfig(StackConfig, AppServicePlanStackSchema):
    include_log_workspace: Optional[bool] = True
    log_workspace_ref_id: Optional[str] = None
    include_keyvault: Optional[bool] = True


def deploy() -> None:
    config: AppserviceSuiteConfig = Confy(AppserviceSuiteConfig).populate()

    # Resource Group
    az_rg: resources.ResourceGroup | resources.AwaitableGetResourceGroupResult = (
        az_resource_group_from_config(config=config)
    )

    pulumi.export("resource_group_name", az_rg.name)

    # Keyvault
    if config.include_keyvault:
        az_kv = az_keyvault_from_config(resource_group=az_rg, config=config)
        pulumi.export("keyvault_name", az_kv.name)
        pulumi.export("keyvault_id", az_kv.id)

    # App Service Plan
    az_asp = az_appservice_plan_from_config(config=config, resource_group=az_rg)
    pulumi.export("appservice_plan_name", az_asp.name)


if __name__ == "__main__" and __package__ is None:
    # When this script is executed with python cli and argument show-config:
    # python appservice_suite_base.py show-config
    # the following code will be executed
    if len(sys.argv) > 1 and sys.argv[1] == "config-schema":
        for config_key in fields(AppserviceSuiteConfig):
            print(f"{config_key.name}")
            print(f"     type: {config_key.type}")

        # Output table
        # Config Key | Type | Optional | Default
        # --------------------------------------
        # include_log_workspace | bool | True | True
        # log_workspace_ref_id | str | True | None

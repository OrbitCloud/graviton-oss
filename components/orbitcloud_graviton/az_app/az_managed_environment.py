from dataclasses import dataclass
from typing import Dict, Optional

import pulumi
from pulumi_azure_native import resources
from pulumi_azure_native.app import v20230501 as app

from orbitcloud_graviton.az_lib import resource_namer
from orbitcloud_graviton.az_lib.config import Confy, StackConfig
from orbitcloud_graviton.az_resources import az_resource_group_from_config


def az_managed_environment(
    workload_name: str,
    env: str,
    location: str,
    resource_group: resources.ResourceGroup | resources.AwaitableGetResourceGroupResult,
    # custom_domain_configuration: Optional[app.CustomDomainConfigurationArgs] = None,
    # kind: Optional[str] = "serverless",
    # sku: Optional[app.sku]
    zone_redundant: Optional[bool] = False,
    # workload_profile: Optional[app.WorkloadProfileArgs] = None,
    # vnet_configuration: Optional[app.VnetConfigurationArgs] = None,
    tags: Optional[Dict[str, str]] = None,
) -> app.ManagedEnvironment:
    environment_name: str = resource_namer(
        resource_type=app.ManagedEnvironment,
        workload_name=workload_name,
        env=env,
        location=location,
    )

    environment: app.ManagedEnvironment = app.ManagedEnvironment(
        environment_name,
        environment_name=environment_name,
        location=location,
        tags=tags,
        resource_group_name=resource_group.name,
        # kind=kind,
        zone_redundant=zone_redundant,
    )

    return environment


def az_managed_environment_from_config(
    config,
    resource_group: resources.ResourceGroup | resources.AwaitableGetResourceGroupResult,
) -> app.ManagedEnvironment:
    if not resource_group and not config.resource_group:
        raise ValueError("Either resource_group or resource_group_name must be set")

    return az_managed_environment(
        workload_name=config.workload_name,
        env=config.env,
        location=config.location,
        resource_group=resource_group,
        # kind=config.kind,
        zone_redundant=config.zone_redundant,
        tags=config.tags,
    )


@dataclass(kw_only=True, frozen=True)
class ManagedEnvironmentConfig(StackConfig):
    kind: Optional[str] = "serverless"
    zone_redundant: Optional[bool] = False


def managed_environment_deploy() -> None:
    config: ManagedEnvironmentConfig = Confy(ManagedEnvironmentConfig).populate()

    # Resource Group
    az_rg: resources.ResourceGroup | resources.AwaitableGetResourceGroupResult = (
        az_resource_group_from_config(config=config)
    )

    pulumi.export("resource_group_name", az_rg.name)

    az_managed_environment = az_managed_environment_from_config(
        config=config, resource_group=az_rg
    )
    pulumi.export(name="managed_environment_name", value=az_managed_environment.name)

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

import pulumi
from pulumi_azure_native import resources
from pulumi_azure_native.app import v20230501 as app
from pulumi_azure_native.network import v20230201 as network

from orbitcloud_graviton.az_lib import resource_namer
from orbitcloud_graviton.az_lib.config import Confy, StackConfig
from orbitcloud_graviton.az_resources import az_resource_group_from_config


class WorkloadProfileTypes(str, Enum):
    Consumption = "Consumption"
    D4 = "D4"
    D8 = "D8"
    D16 = "D16"
    D32 = "D32"
    E4 = "E4"
    E8 = "E8"
    E16 = "E16"
    E32 = "E32"
    NC24A100 = "NC24-A100"
    NC48A100 = "NC48-A100"
    NC96A100 = "NC96-A100"


@dataclass
class WorkloadProfile:
    workload_profile_type: WorkloadProfileTypes
    name: str  # TODO: Add some validation for name, should be max 15 chars - naming p_x_type? (p_web_d4)
    minimum_count: Optional[int] = 0
    maximum_count: Optional[int] = 3


def az_managed_environment(
    workload_name: str,
    env: str,
    location: str,
    resource_group: resources.ResourceGroup | resources.AwaitableGetResourceGroupResult,
    # custom_domain_configuration: Optional[app.CustomDomainConfigurationArgs] = None,
    zone_redundant: Optional[bool] = False,
    environment_type: Optional[str] = "WorkloadProfiles",
    workload_profiles: Optional[list[dict]] = None,
    vnet_config_subnet: Optional[network.Subnet | network.AwaitableGetSubnetResult | str] = None,
    vnet_config_internal: Optional[bool] = True,
    tags: Optional[Dict[str, str]] = None,
) -> app.ManagedEnvironment:
    environment_name: str = resource_namer(
        resource_type=app.ManagedEnvironment,
        workload_name=workload_name,
        env=env,
        location=location,
    )

    # Handle Environment Type / Workload Profiles
    workload_profiles_args: list[app.WorkloadProfileArgs] = []

    if environment_type not in ["WorkloadProfiles", "ConsumptionOnly"]:
        raise ValueError("environment_type must be either 'WorkloadProfiles' or 'ConsumptionOnly'")

    if environment_type == "WorkloadProfiles":
        if workload_profiles is None:
            workload_profiles_args.append(
                app.WorkloadProfileArgs(name="Consumption", workload_profile_type="Consumption")
            )
        if workload_profiles is not None:
            for profile in workload_profiles:
                workload_profile_arg = app.WorkloadProfileArgs(
                    workload_profile_type=profile.get("workload_profile_type"),  # type: ignore
                    name=profile.get("name"),  # type: ignore
                    minimum_count=profile.get("minimum_count"),
                    maximum_count=profile.get("maximum_count"),
                )
                workload_profiles_args.append(workload_profile_arg)
    elif environment_type == "ConsumptionOnly" and workload_profiles is not None:
        pulumi.warn(
            "ConsumptionOnly environments does not support workload profiles. "
            "workload_profiles will be ignored. If you want to use workload profiles, "
            "please use environment_type='WorkloadProfiles'."
        )

    # If zone_redundant == True, VNET integration is required
    if zone_redundant and not vnet_config_subnet:
        raise ValueError("VNET config required for Zone Redundancy. Please provide a subnet.")

    # Handle VNet Configuration
    vnet_config_args = None
    infrastructure_resource_group_name: str = ""
    if vnet_config_subnet:
        subnet = vnet_config_subnet
        if isinstance(subnet, (network.Subnet, network.AwaitableGetSubnetResult)):
            subnet_id = subnet.id
        elif isinstance(subnet, str):
            subnet_id = subnet
        else:
            raise TypeError("subnet must be either a network.Subnet object or a subnet ID string")
        print(f"vnet_config_internal: {vnet_config_internal}")
        vnet_config_args = app.VnetConfigurationArgs(
            infrastructure_subnet_id=subnet_id,
            internal=vnet_config_internal,
        )

        # When VNET integrated, a separate resource group is automatically created for the LB - here we can specify the RG name instead of having it auto-generated.
        infrastructure_resource_group_name: str = f"rg-infra-{environment_name}"

    environment: app.ManagedEnvironment = app.ManagedEnvironment(
        environment_name,
        environment_name=environment_name,
        location=location,
        tags=tags,
        resource_group_name=resource_group.name,
        workload_profiles=workload_profiles_args,
        vnet_configuration=vnet_config_args,
        zone_redundant=zone_redundant,
        infrastructure_resource_group=infrastructure_resource_group_name,
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
        workload_profiles=config.workload_profiles,
        environment_type=config.environment_type,
        zone_redundant=config.zone_redundant,
        vnet_config_subnet=config.vnet_config_subnet,
        vnet_config_internal=config.vnet_config_internal,
        tags=config.tags,
    )


@dataclass(kw_only=True, frozen=True)
class ManagedEnvironmentConfig(StackConfig):
    zone_redundant: Optional[bool] = False
    workload_profiles: Optional[list[WorkloadProfile]] = None
    environment_type: Optional[str] = "WorkloadProfiles"
    vnet_config_subnet: Optional[str] = None
    vnet_config_internal: Optional[bool] = True


def managed_environment_deploy() -> None:
    config: ManagedEnvironmentConfig = Confy(ManagedEnvironmentConfig).populate()

    print(config)

    # Resource Group
    az_rg: resources.ResourceGroup | resources.AwaitableGetResourceGroupResult = az_resource_group_from_config(
        config=config
    )

    pulumi.export("resource_group_name", az_rg.name)

    az_managed_environment = az_managed_environment_from_config(config=config, resource_group=az_rg)
    pulumi.export(name="managed_environment_name", value=az_managed_environment.name)

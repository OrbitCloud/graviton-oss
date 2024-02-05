from typing import Optional

import pulumi
from pulumi_azure_native import insights, operationalinsights
from pulumi_azure_native.app import v20230501 as app
from pydantic import BaseModel, SecretStr, field_validator
from pydantic_core.core_schema import FieldValidationInfo

from orbitcloud_graviton.az_lib import get_resource_name_from_id
from orbitcloud_graviton.az_monitor import az_diagnosticsetting
from orbitcloud_graviton.pulumi_lib import AzureBase, PulumiConfig, get_azure_stack

from ._certificate import CertificateConfig, certificate


class ManagedEnvironmentConfig(BaseModel):
    environment_type: Optional[str] = "WorkloadProfiles"
    certificates: Optional[list[dict]] = None
    workload_profiles: Optional[list[dict]] = None
    vnet_config_subnet: Optional[str] = None
    vnet_config_internal: Optional[bool] = True
    custom_domain_name: Optional[str] = None
    custom_domain_certificate_password: Optional[SecretStr] = None
    custom_domain_certificate_value: Optional[SecretStr] = None
    zone_redundant: Optional[bool] = False
    log_workspace_ref: Optional[str] = None

    @field_validator("zone_redundant")
    def validate_zone_redundant(cls, v, info: FieldValidationInfo):
        if v and not info.data["vnet_config_subnet"]:
            raise ValueError("VNET config required for Zone Redundancy. Please provide a subnet.")
        return v

    @field_validator("environment_type")
    def validate_environment_type(cls, v):
        if v not in ["WorkloadProfiles", "ConsumptionOnly"]:
            raise ValueError("environment_type must be either 'WorkloadProfiles' or 'ConsumptionOnly'")
        return v

    @field_validator("workload_profiles")
    def validate_workload_profiles(cls, v, info: FieldValidationInfo):
        if info.data.get("environment_type") == "ConsumptionOnly" and v:
            raise ValueError("ConsumptionOnly environments do not support workload profiles.")
        return v


def containerapp_environment(
    stack: AzureBase,
    config: ManagedEnvironmentConfig,
    opts: Optional[pulumi.ResourceOptions] = None,
) -> app.ManagedEnvironment:
    environment_name = stack.name_for(app.ManagedEnvironment)
    print(f"environment_name = {environment_name}")
    # Handle Environment Type / Workload Profiles
    workload_profiles_args: list[app.WorkloadProfileArgs] = []
    if config.environment_type == "WorkloadProfiles":
        if config.workload_profiles is None:
            workload_profiles_args.append(
                app.WorkloadProfileArgs(name="Consumption", workload_profile_type="Consumption")
            )
        if config.workload_profiles:
            for profile in config.workload_profiles:
                workload_profile_arg = app.WorkloadProfileArgs(
                    workload_profile_type=profile.get("workload_profile_type"),  # type: ignore
                    name=profile.get("name"),  # type: ignore
                    minimum_count=profile.get("minimum_count"),
                    maximum_count=profile.get("maximum_count"),
                )
                workload_profiles_args.append(workload_profile_arg)

    # Handle VNet Configuration
    vnet_config_args = None
    infrastructure_resource_group_name: str = ""
    if config.vnet_config_subnet:
        print(f"vnet_config_internal: {config.vnet_config_internal}")
        vnet_config_args = app.VnetConfigurationArgs(
            infrastructure_subnet_id=config.vnet_config_subnet,
            internal=config.vnet_config_internal,
        )

        # When VNET integrated, a separate resource group is automatically created for the LB - here we can specify the RG name instead of having it auto-generated. -to-be-discussed
        infrastructure_resource_group_name = stack.resource_group.name.apply(lambda name: f"{name}-CAE_INFRA")

    # Handle Custom Domain
    custom_domain_args = None
    if (
        config.custom_domain_name
        and config.custom_domain_certificate_password
        and config.custom_domain_certificate_value
    ):
        custom_domain_args = app.CustomDomainConfigurationArgs(
            certificate_password=config.custom_domain_certificate_password.get_secret_value(),
            certificate_value=config.custom_domain_certificate_value.get_secret_value(),
            dns_suffix=config.custom_domain_name,
        )

    app_logs_args = app.AppLogsConfigurationArgs(destination="azure-monitor")

    environment = app.ManagedEnvironment(
        resource_name=environment_name,
        environment_name=environment_name,
        resource_group_name=stack.resource_group.name,
        location=stack.location,
        workload_profiles=workload_profiles_args,
        custom_domain_configuration=custom_domain_args,
        app_logs_configuration=app_logs_args,
        vnet_configuration=vnet_config_args,
        zone_redundant=config.zone_redundant,
        infrastructure_resource_group=infrastructure_resource_group_name,
        opts=opts,
    )

    if config.log_workspace_ref:
        log_workspace = operationalinsights.Workspace.get(
            resource_name=get_resource_name_from_id(config.log_workspace_ref),
            id=config.log_workspace_ref,
        )
        _az_containerapp_env_diagnostic(
            resource=environment,
            log_workspace=log_workspace,
        )

    # Handle Certificates
    if config.certificates:
        pulumi.Output.all(environment.name).apply(
            lambda _: [
                certificate(
                    stack=stack,
                    config=CertificateConfig(
                        certificate_name=cert["name"],
                        certificate_value=cert["value"],
                        certificate_password=cert["password"],
                        environment_name=environment_name,  # Ensure this matches the created environment's name
                    ),
                    opts=opts,
                )
                for cert in config.certificates  # type: ignore
            ]
        )

    return environment


class ManagedEnvConfig(PulumiConfig):
    containerapp_env: ManagedEnvironmentConfig


def deploy_containerapp_environment():
    config: ManagedEnvConfig = ManagedEnvConfig.model_validate({})

    stack: AzureBase = get_azure_stack()

    environment = containerapp_environment(
        stack=stack,
        config=config.containerapp_env,
    )

    return environment


def _az_containerapp_env_diagnostic(
    resource: app.ManagedEnvironment,
    log_workspace: operationalinsights.Workspace,
) -> insights.DiagnosticSetting:
    settings = az_diagnosticsetting(
        resource=resource,
        log_workspace=log_workspace,
        metric_categories=["AllMetrics"],
        log_categories=["ContainerAppConsoleLogs", "ContainerAppSystemLogs", "AppEnvSpringAppConsoleLogs"],
        opts=pulumi.ResourceOptions(parent=resource),
    )
    return settings

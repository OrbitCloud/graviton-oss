from typing import Annotated, List, Literal, Optional, Union

import pulumi
from pulumi_azure_native import insights, operationalinsights
from pulumi_azure_native.app import v20230501 as app
from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from orbitcloud_graviton.az_lib import get_resource_name_from_id
from orbitcloud_graviton.az_lib.types import AzureIdRef
from orbitcloud_graviton.az_monitor import az_diagnosticsetting
from orbitcloud_graviton.pulumi_lib import AzureBase, PulumiConfig, get_azure_stack
from orbitcloud_graviton.pulumi_lib.types import DomainName

from ._certificate import CertificateConfig, certificate


class ConsumptionProfile(BaseModel):
    workload_type: Literal["Consumption"] = "Consumption"
    name: Literal["Consumption"] = "Consumption"


class DedicatedProfile(BaseModel):
    name: str
    workload_type: Literal["D4", "D8", "E4", "E8"]
    minimum_count: Annotated[int, Field(ge=0)]
    maximum_count: Annotated[int, Field(gt=0)]


class CustomDomain(BaseModel):
    dns_suffix: DomainName
    cert_password: SecretStr
    cert_contents: SecretStr


class ContainerAppEnvConfig(BaseModel):
    workload_profiles: list[Union[ConsumptionProfile, DedicatedProfile]] = Field(
        discriminator="workload_type", default_factory=lambda: [ConsumptionProfile()]
    )

    subnet_id: Optional[AzureIdRef] = None
    zone_redundant: Optional[bool] = False
    public_network_access: Optional[bool] = False

    certificates: Optional[List[CertificateConfig]] = None
    custom_domain: Optional[CustomDomain] = None

    log_workspace_ref: Optional[str] = None

    @model_validator(mode="after")
    def zone_redundancy_requires_subnet(m: "ContainerAppEnvConfig") -> "ContainerAppEnvConfig":
        if m.zone_redundant and not m.subnet_id:
            raise ValueError("VNET config required for Zone Redundancy. Please provide a subnet.")
        return m

    model_config = ConfigDict(arbitrary_types_allowed=True)


def containerapp_environment(
    stack: AzureBase,
    config: ContainerAppEnvConfig,
    opts: Optional[pulumi.ResourceOptions] = None,
) -> app.ManagedEnvironment:
    environment_name = stack.name_for(app.ManagedEnvironment)

    workload_profiles_args: list[app.WorkloadProfileArgs] = [
        app.WorkloadProfileArgs(
            workload_profile_type=profile.workload_type,
            name=str(profile.name),
            minimum_count=profile.minimum_count if isinstance(profile, DedicatedProfile) else None,
            maximum_count=profile.maximum_count if isinstance(profile, DedicatedProfile) else None,
        )
        for profile in config.workload_profiles
    ]

    vnet_args: app.VnetConfigurationArgs | None = (
        app.VnetConfigurationArgs(
            infrastructure_subnet_id=config.subnet_id,
            internal=(not config.public_network_access),
        )
        if config.subnet_id
        else None
    )

    # Handle Custom Domain
    custom_domain_args = (
        app.CustomDomainConfigurationArgs(
            certificate_password=config.custom_domain.cert_password.get_secret_value(),
            certificate_value=config.custom_domain.cert_contents.get_secret_value(),
            dns_suffix=config.custom_domain.dns_suffix,
        )
        if config.custom_domain
        else None
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
        vnet_configuration=vnet_args,
        zone_redundant=config.zone_redundant,
        # When VNET integrated, a separate resource group is automatically created for the LB
        # here we can specify the RG name instead of having it auto-generated. -to-be-discussed
        infrastructure_resource_group=(
            stack.resource_group.name.apply(lambda name: f"{name}-CAE_INFRA")
            if config.subnet_id
            else None
        ),
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

    certs: list[app.Certificate] = (  # noqa
        (
            [
                certificate(
                    stack=stack,
                    environment=environment,
                    cert=cert,
                    opts=opts,
                )
                for cert in config.certificates
            ]
        )
        if config.certificates
        else []
    )

    return environment


class ManagedEnvConfig(PulumiConfig):
    containerapp_env: ContainerAppEnvConfig


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
        log_categories=[
            "ContainerAppConsoleLogs",
            "ContainerAppSystemLogs",
            "AppEnvSpringAppConsoleLogs",
        ],
        opts=pulumi.ResourceOptions(parent=resource),
    )
    return settings

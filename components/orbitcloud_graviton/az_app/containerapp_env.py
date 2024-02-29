from typing import List, Optional, Union

import pulumi
from pulumi_azure_native import insights, network
from pulumi_azure_native.app import v20230801preview as app
from pydantic import BaseModel, ConfigDict, Field, model_validator

from orbitcloud_graviton.az_lib.types import AzureIdRef, DictRef, StrRef
from orbitcloud_graviton.az_monitor import diagnostic_setting
from orbitcloud_graviton.az_network.dns_zone import DnsZone, DnsZoneConfig
from orbitcloud_graviton.az_network.types import ARecord, TxtRecord
from orbitcloud_graviton.pulumi_lib import AzureBase
from orbitcloud_graviton.pulumi_lib.types import DomainName

from ._schema import ConsumptionProfile, DedicatedProfile
from .certificate import CertificateConfig, certificate


class CustomDomain(BaseModel):
    name: DomainName
    dns_zone_id: Optional[AzureIdRef] = None
    dns_zone_stack: Optional[DictRef] = None

    cert_value: StrRef
    cert_pass: StrRef

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ContainerAppEnvConfig(BaseModel):
    workload_profiles: list[Union[ConsumptionProfile, DedicatedProfile]] = Field(
        discriminator="workload_type",
        default_factory=lambda: [ConsumptionProfile()],
        title="Workload Profiles",
        description="List of workload profiles for instances behind the Container App Environment.",
    )

    subnet_id: Optional[AzureIdRef] = Field(
        default=None,
        title="Subnet to run in",
        description="The subnet to run the Container App Environment in. Required for Zone Redundancy.",
        examples=[
            "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-name/providers/Microsoft.Network/virtualNetworks/vnet-name/subnets/subnet-name"
            "stack://project/stack-name/output-name",
            "stack://project/stack-name/output-name.subnet_id",
            "stack://project/stack-name/output-name.subnets.subnet_id",
        ],
    )
    zone_redundant: Optional[bool] = False
    public_network_access: Optional[bool] = False

    certificates: Optional[List[CertificateConfig]] = None

    custom_domain: Optional[CustomDomain] = None

    dapr_appi_connstring: Optional[Union[str, pulumi.Output]] = None
    dapr_appi_instrumentation_key: Optional[Union[str, pulumi.Output]] = None

    log_workspace_id: Optional[AzureIdRef] = None

    @model_validator(mode="after")
    def zone_redundancy_requires_subnet(m: "ContainerAppEnvConfig") -> "ContainerAppEnvConfig":
        if m.zone_redundant and not m.subnet_id:
            raise ValueError(
                "subnet_id config required for Zone Redundancy. Please provide a subnet."
            )
        return m

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ContainerAppEnv(pulumi.ComponentResource):
    def __init__(
        self,
        stack: AzureBase,
        config: ContainerAppEnvConfig,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        self.stack: AzureBase = stack
        self.config: ContainerAppEnvConfig = config

        super().__init__(
            "Graviton:az_app:ContainerAppEnv",
            name=f"cae-{self.stack.workload_name}",
            props=None,
            opts=opts,
        )
        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts1=opts, opts2=pulumi.ResourceOptions(parent=self)
        )

        self.environment: app.ManagedEnvironment = self._environment()
        self.dns_records: List[network.RecordSet] | None = self._dns_records()
        self.certificates: list[app.Certificate] | None = self._certificates()
        self._diagnostic_settings()

        self._outputs()

    def _environment(self) -> app.ManagedEnvironment:
        environment = app.ManagedEnvironment(
            resource_name=self.stack.name_for(resource_type=app.ManagedEnvironment),
            environment_name=self.stack.name_for(resource_type=app.ManagedEnvironment),
            resource_group_name=self.stack.resource_group.name,
            location=self.stack.location,
            # Workload config
            workload_profiles=self._workload_profiles(),
            zone_redundant=self.config.zone_redundant,
            # Logging
            app_logs_configuration=app.AppLogsConfigurationArgs(destination="azure-monitor"),
            dapr_ai_connection_string=self.config.dapr_appi_connstring,
            dapr_ai_instrumentation_key=self.config.dapr_appi_instrumentation_key,
            # Custom domain config
            custom_domain_configuration=self._custom_domain(),
            # VNET config
            vnet_configuration=self._vnet_config(),
            infrastructure_resource_group=(
                self.stack.resource_group.name.apply(lambda name: f"{name}-CAE_INFRA")
                if self.config.subnet_id
                else None
            ),  # When VNET integrated, a separate resource group is automatically created for the LB
            opts=self._opts,
        )

        return environment

    def _dns_records(self) -> List[network.RecordSet] | None:
        if self.config.custom_domain and self.config.custom_domain.dns_zone_id:
            if self.config.custom_domain.dns_zone_stack and isinstance(
                self.config.custom_domain.dns_zone_stack, dict
            ):
                stack_args = self.config.custom_domain.dns_zone_stack
                stack_args["skip_exports"] = True
                stack = AzureBase.model_validate(obj=stack_args)

            zone = DnsZone(
                dns_zone_id=self.config.custom_domain.dns_zone_id,
                config=DnsZoneConfig(
                    name=self.config.custom_domain.name,
                    records=[
                        ARecord(
                            relative_name="*",
                            ip_addresses=[self.environment.static_ip],
                        ),
                        TxtRecord(
                            relative_name="asuid",
                            values=[
                                self.environment.custom_domain_configuration.custom_domain_verification_id
                            ],
                        ),
                    ],
                ),
                stack=stack or self.stack,
                opts=self._opts,
            )
            return zone.records

    def _workload_profiles(self) -> list[app.WorkloadProfileArgs]:
        return [
            app.WorkloadProfileArgs(
                workload_profile_type=profile.workload_type,
                name=profile.name,
                minimum_count=(
                    profile.minimum_count if isinstance(profile, DedicatedProfile) else None
                ),
                maximum_count=(
                    profile.maximum_count if isinstance(profile, DedicatedProfile) else None
                ),
            )
            for profile in self.config.workload_profiles
        ]

    def _vnet_config(self) -> app.VnetConfigurationArgs | None:
        return (
            app.VnetConfigurationArgs(
                infrastructure_subnet_id=self.config.subnet_id,
                internal=(not self.config.public_network_access),
            )
            if self.config.subnet_id
            else None
        )

    def _custom_domain(self) -> app.CustomDomainConfigurationArgs | None:
        if not self.config.custom_domain:
            return None

        return app.CustomDomainConfigurationArgs(
            certificate_password=str(self.config.custom_domain.cert_pass),
            certificate_value=str(self.config.custom_domain.cert_value),
            dns_suffix=self.config.custom_domain.name,
        )

    def _diagnostic_settings(self) -> insights.DiagnosticSetting | None:
        if self.config.log_workspace_id:
            return diagnostic_setting(
                resource=self.environment,
                log_workspace_id=self.config.log_workspace_id,
                metric_categories=["AllMetrics"],
                log_categories=[
                    "ContainerAppConsoleLogs",
                    "ContainerAppSystemLogs",
                    "AppEnvSpringAppConsoleLogs",
                ],
                opts=pulumi.ResourceOptions(parent=self.environment),
            )

    def _certificates(self) -> list[app.Certificate] | None:
        if self.config.certificates:
            return [
                certificate(
                    stack=self.stack,
                    environment=self.environment,
                    cert=cert,
                    opts=self._opts,
                )
                for cert in self.config.certificates
            ]

    def _outputs(self) -> None:
        self.register_outputs(
            outputs={
                "environment": self.environment,
                "certificates": self.certificates,
            }
        )
        pulumi.export(
            name="containerapp_env",
            value={
                "id": self.environment.id,
                "name": self.environment.name,
                "static_ip": self.environment.static_ip,
                "custom_domain_verification_id": self.environment.custom_domain_configuration.custom_domain_verification_id,
            },
        )

from typing import Dict, List, Optional

import pulumi
from pulumi_azure_native import insights
from pulumi_azure_native.app import v20231102preview as pam_app
from pydantic import BaseModel, ConfigDict, model_validator

from orbitcloud_graviton.az_app._app_schema import ContainerProbeConfig, ContainerResourcesConfig
from orbitcloud_graviton.az_app.outputs import ContainerAppEnvOutput
from orbitcloud_graviton.az_lib.types import AzureIdRef, DictRef
from orbitcloud_graviton.az_monitor import diagnostic_setting
from orbitcloud_graviton.pulumi_lib import AzureBase


class ContainerAppScaleConfig(BaseModel):
    max_replicas: Optional[int] = 10
    min_replicas: Optional[int] = 1

    @model_validator(mode="after")
    def min_replicas_or_max_replicas(m: "ContainerAppScaleConfig") -> "ContainerAppScaleConfig":
        if not m.min_replicas and not m.max_replicas:
            raise ValueError("Either min_replicas or max_replicas must be set.")
        return m

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class CustomDomainConfig(BaseModel):
    name: str
    certificate_id: Optional[AzureIdRef] = None
    binding_type: Optional[pam_app.BindingType] = pam_app.BindingType.SNI_ENABLED
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class IngressConfig(BaseModel):
    client_certificate_mode: pam_app.IngressClientCertificateMode = (
        pam_app.IngressClientCertificateMode.IGNORE
    )
    external: Optional[bool] = False
    https_only: Optional[bool] = True
    target_port: int
    custom_domains: Optional[List[CustomDomainConfig]] = None


class ContainerConfig(BaseModel):
    name: str
    image: str
    probes: Optional[List[ContainerProbeConfig]] = None  # noqa: F821
    resources: ContainerResourcesConfig = ContainerResourcesConfig()

    env_vars: Optional[dict[str, str]] = None
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ContainerAppConfig(BaseModel):
    environment_output_ref: DictRef
    workload_profile_name: str
    containers: list[ContainerConfig]
    scaling: Optional[ContainerAppScaleConfig] = ContainerAppScaleConfig()
    ingress: IngressConfig
    log_workspace_id: Optional[AzureIdRef] = None

    @model_validator(mode="after")
    def validate_resources(m: "ContainerAppConfig") -> "ContainerAppConfig":
        if m.workload_profile_name == "Consumption":
            for container in m.containers:
                container.resources.validate_consumption_combinations()
        return m

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ContainerApp(pulumi.ComponentResource):
    def __init__(
        self,
        stack: AzureBase,
        config: ContainerAppConfig,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        self.stack: AzureBase = stack
        self.config: ContainerAppConfig = config

        super().__init__(
            "Graviton:ContainerApp",
            name=f"containerapp-{stack.workload_name}-{stack.env}",
            props=None,
            opts=opts,
        )

        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts1=opts, opts2=pulumi.ResourceOptions(parent=self)
        )

        self.app_name: str = self.stack.name_for(resource_type=pam_app.ContainerApp)
        self.environment: ContainerAppEnvOutput = self._get_environment()
        self.app: pam_app.ContainerApp = self._container_app()

        self._outputs()

    def _get_environment(self) -> ContainerAppEnvOutput:
        if not self.config.environment_output_ref or not isinstance(
            self.config.environment_output_ref, dict
        ):
            raise ValueError("environment_output_ref is required.")

        env: ContainerAppEnvOutput = ContainerAppEnvOutput.model_validate(
            self.config.environment_output_ref
        )
        if not env or not env.id:
            raise ValueError("environment_output_ref is required.")

        return env

    def _container_app(self) -> pam_app.ContainerApp:
        return pam_app.ContainerApp(
            resource_name=self.app_name,
            args=pam_app.ContainerAppArgs(
                resource_group_name=self.stack.resource_group.name,
                location=self.stack.location,
                container_app_name=self.stack.name_for(resource_type=pam_app.ContainerApp),
                identity=pam_app.ManagedServiceIdentityArgs(type="SystemAssigned"),
                managed_environment_id=str(self.environment.id),
                workload_profile_name=self.config.workload_profile_name,
                template=self._containers(),
                configuration=self._container_configuration_args(),
            ),
            opts=self._opts,
        )

    def _containers(self) -> pam_app.TemplateArgs:
        _containers: list[pam_app.ContainerArgs] = []
        for container in self.config.containers:
            _containers.append(
                pam_app.ContainerArgs(
                    name=container.name,
                    image=container.image,
                    env=self._container_env_vars(container.env_vars)
                    if container.env_vars
                    else None,
                    resources=pam_app.ContainerResourcesArgs(
                        cpu=container.resources.cpu,
                        memory=str(container.resources.memory_gb) + "Gi",
                    ),
                )
            )
        return pam_app.TemplateArgs(
            containers=_containers,
            scale=pam_app.ScaleArgs(
                min_replicas=self.config.scaling.min_replicas,
                max_replicas=self.config.scaling.max_replicas,
            )
            if self.config.scaling
            else None,
        )

    def _dapr_args(self) -> pam_app.DaprArgs:
        return pam_app.DaprArgs(
            app_id=self.app_name,
            enabled=True,
            enable_api_logging=True,
            app_port=self.config.ingress.target_port,
            app_protocol="http",
            log_level=pam_app.LogLevel.DEBUG,
        )

    def _container_configuration_args(self) -> pam_app.ConfigurationArgs:
        return pam_app.ConfigurationArgs(
            ingress=pam_app.IngressArgs(
                allow_insecure=not self.config.ingress.https_only,
                external=self.config.ingress.external,
                target_port=self.config.ingress.target_port,
                custom_domains=self._custom_domain_args(),
            )
        )

    def _custom_domain_args(self) -> List[pam_app.CustomDomainArgs] | None:
        if not self.config.ingress.custom_domains:
            return None
        _domains = []
        for domain in self.config.ingress.custom_domains:
            _domains.append(
                pam_app.CustomDomainArgs(
                    name=domain.name,
                    certificate_id=domain.certificate_id,
                    binding_type=domain.binding_type,
                )
            )
            # self._managed_certificate(custom_domain=domain.name)
        return _domains

    def _managed_certificate(self, custom_domain: str) -> pam_app.ManagedCertificate | None:
        if not self.environment or not self.environment.id:
            return None

        pam_app.ManagedCertificate(
            resource_name="cert",
            args=pam_app.ManagedCertificateArgs(
                resource_group_name=self.environment.resource_group_name,
                environment_name=self.environment.name,
                managed_certificate_name=custom_domain,
                properties=pam_app.ManagedCertificatePropertiesArgs(
                    domain_control_validation=pam_app.ManagedCertificateDomainControlValidation.HTTP,
                    subject_name=custom_domain,
                ),
                location=self.stack.location,
            ),
            opts=pulumi.ResourceOptions(custom_timeouts=pulumi.CustomTimeouts(create="1m")),
        )

    def _container_env_vars(self, env_vars: Dict[str, str]) -> List[pam_app.EnvironmentVarArgs]:
        return [
            pam_app.EnvironmentVarArgs(
                name=key,
                value=val,
            )
            for key, val in env_vars.items()
        ]

    def _diagnostic_settings(self) -> insights.DiagnosticSetting | None:
        if self.config.log_workspace_id:
            return diagnostic_setting(
                resource=self.app,
                log_workspace_id=self.config.log_workspace_id,
                metric_categories=["AllMetrics"],
                log_categories=[
                    "SomeCategory",
                ],
                opts=pulumi.ResourceOptions(parent=self.app),
            )

    def _outputs(self) -> None:
        self.register_outputs(
            {"some_resource": self.app},
        )

        self.stack.export(
            exports={
                "app": {
                    "id": self.app.id,
                    "name": self.app.name,
                    "endpoints": {
                        "default_url": self.app.configuration.ingress.fqdn.apply(
                            lambda x: f"https://{x}",
                        ),
                        "custom_domains": (
                            self.app.configuration.ingress.custom_domains
                            if self.app.configuration.ingress.custom_domains
                            else None
                        ),
                        "revision": {
                            "latest_revision_fqdn": self.app.latest_revision_fqdn,
                            "latest_revision_name": self.app.latest_revision_name,
                            "latest_ready_revision_name": self.app.latest_ready_revision_name,
                        },
                    },
                }
            }
        )

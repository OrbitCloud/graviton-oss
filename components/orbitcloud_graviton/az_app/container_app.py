from typing import Dict, List, Literal, Optional, Union

import pulumi
from pulumi_azure_native.app import v20240301 as pam_app
from pulumi_azure_native.app.v20231102preview import (
    AppResiliency,
    AppResiliencyArgs,
    CircuitBreakerPolicyArgs,
    HttpConnectionPoolArgs,
    HttpRetryPolicyArgs,
    TcpConnectionPoolArgs,
    TcpRetryPolicyArgs,
    TimeoutPolicyArgs,
)
from pydantic import BaseModel, ConfigDict, Field, model_validator

from orbitcloud_graviton.az_acr.outputs import AdminUserEnabledRegistryOutput
from orbitcloud_graviton.az_app.outputs import ContainerAppEnvOutput
from orbitcloud_graviton.az_iam.assignment import IamAssignmentConfig, iam_assignment
from orbitcloud_graviton.az_lib.types import AzureIdRef, DictRef, StrRef
from orbitcloud_graviton.az_network.types import PrivateIPv4Network, PublicIPv4Network
from orbitcloud_graviton.pulumi_lib import AzureStack

from ._app_schema import AppResiliencyConfig, ContainerProbeConfig, ContainerResourcesConfig


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


class HttpIngressConfig(BaseModel):
    protocol: Literal["http"]
    client_certificate_mode: pam_app.IngressClientCertificateMode = (
        pam_app.IngressClientCertificateMode.IGNORE
    )
    https_only: Optional[bool] = True
    external: Optional[bool] = False
    custom_domains: Optional[List[CustomDomainConfig]] = None
    ip_allow_list: Optional[List[Union[PrivateIPv4Network, PublicIPv4Network, StrRef]]] = Field(
        ..., default_factory=list
    )
    target_port: int
    sticky_sessions: Optional[pam_app.Affinity] = pam_app.Affinity.NONE

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class TcpIngressConfig(BaseModel):
    protocol: Literal["tcp"]
    target_port: int
    exposed_port: Optional[int] = None
    external: Optional[bool] = False
    custom_domains: Optional[List[CustomDomainConfig]] = None
    ip_allow_list: Optional[List[Union[PrivateIPv4Network, PublicIPv4Network, StrRef]]] = Field(
        default_factory=list
    )

    @model_validator(mode="after")
    def validate_exposed_port(m: "TcpIngressConfig") -> "TcpIngressConfig":
        if (m.external and m.exposed_port) and not m.ip_allow_list:
            pulumi.warn(
                msg="External TCP ingress is configured without IP allow list. Are you sure?"
            )
        return m

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ContainerConfig(BaseModel):
    name: str
    image: str
    from_public_registry: Optional[bool] = False

    probes: Optional[List[ContainerProbeConfig]] = None
    resources: ContainerResourcesConfig = ContainerResourcesConfig()

    env_vars: Optional[dict[str, StrRef | str]] = None
    env_secrets: Optional[dict[str, str]] = None
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ContainerAppConfig(BaseModel):
    name: Optional[str] = None
    environment_output_ref: DictRef
    workload_profile_name: str
    containers: list[ContainerConfig]
    revision_mode: Optional[pam_app.ActiveRevisionsMode] = pam_app.ActiveRevisionsMode.SINGLE
    secrets: Optional[Dict[str, StrRef | str]] = Field(default_factory=dict)
    scaling: Optional[ContainerAppScaleConfig] = ContainerAppScaleConfig()
    resiliency: Optional[AppResiliencyConfig] = None
    ingress: HttpIngressConfig | TcpIngressConfig = Field(..., discriminator="protocol")
    log_workspace_id: Optional[AzureIdRef] = None
    registry_output_ref: Optional[DictRef] = None

    azure_permissions: Optional[List[IamAssignmentConfig]] = None

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
        stack: AzureStack,
        config: ContainerAppConfig,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        self.stack: AzureStack = stack
        self.config: ContainerAppConfig = config

        super().__init__(
            "Graviton:ContainerApp",
            name=f"containerapp-{self.config.name or stack.workload_name}-{stack.env}",
            props=None,
            opts=opts,
        )

        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts1=opts, opts2=pulumi.ResourceOptions(parent=self)
        )

        self.app_name: str = self.stack.name_for(
            resource_type=pam_app.ContainerApp, workload_name=self.config.name
        )

        self.secrets: Dict[str, StrRef | str] = self.config.secrets or {}
        self.registry: AdminUserEnabledRegistryOutput | None = self._get_registry()
        self.environment: ContainerAppEnvOutput = self._get_environment()
        self.app: pam_app.ContainerApp = self._container_app()
        self.resiliency: AppResiliency | None = self._app_resiliency()
        self._azure_permissions()

        self._outputs()

    def _get_environment(self) -> ContainerAppEnvOutput:
        return ContainerAppEnvOutput.model_validate(self.config.environment_output_ref)

    def _get_registry(self) -> AdminUserEnabledRegistryOutput | None:
        if not self.config.registry_output_ref:
            return None

        registry_output: AdminUserEnabledRegistryOutput = (
            AdminUserEnabledRegistryOutput.model_validate(self.config.registry_output_ref)
        )
        self.secrets["registry-secret"] = registry_output.admin_credentials["password"]
        return registry_output

    def _container_app(self) -> pam_app.ContainerApp:
        return pam_app.ContainerApp(
            resource_name=self.app_name,
            args=pam_app.ContainerAppArgs(
                resource_group_name=self.stack.resource_group.name,
                location=self.stack.location,
                container_app_name=self.app_name,
                identity=pam_app.ManagedServiceIdentityArgs(type="SystemAssigned"),
                managed_environment_id=str(self.environment.id),
                workload_profile_name=self.config.workload_profile_name,
                template=self._containers(),
                configuration=self._app_configuration_args(),
            ),
            opts=self._opts,
        )

    def _containers(self) -> pam_app.TemplateArgs:
        _containers: list[pam_app.ContainerArgs] = []
        for container in self.config.containers:
            image: pulumi.Output[str] | str = (
                pulumi.Output.concat(self.registry.login_server, "/", container.image)
                if self.registry and not container.from_public_registry
                else container.image
            )
            _containers.append(
                pam_app.ContainerArgs(
                    name=container.name,
                    image=image,
                    env=self._container_env_vars(container=container),
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

    def _app_configuration_args(self) -> pam_app.ConfigurationArgs:
        return pam_app.ConfigurationArgs(
            active_revisions_mode=self.config.revision_mode,
            ingress=pam_app.IngressArgs(
                allow_insecure=not self.config.ingress.https_only
                if isinstance(self.config.ingress, HttpIngressConfig)
                else False,
                external=self.config.ingress.external
                if hasattr(self.config.ingress, "external")
                else False,
                target_port=self.config.ingress.target_port,
                custom_domains=self._custom_domain_args(),
                client_certificate_mode=self.config.ingress.client_certificate_mode
                if isinstance(self.config.ingress, HttpIngressConfig)
                else None,
                exposed_port=self.config.ingress.exposed_port
                if isinstance(self.config.ingress, TcpIngressConfig)
                else None,
                sticky_sessions=pam_app.IngressStickySessionsArgs(
                    affinity=self.config.ingress.sticky_sessions,
                )
                if isinstance(self.config.ingress, HttpIngressConfig)
                else None,
                transport=pam_app.IngressTransportMethod.TCP
                if self.config.ingress.protocol == "tcp"
                else pam_app.IngressTransportMethod.AUTO,
                ip_security_restrictions=[
                    pam_app.IpSecurityRestrictionRuleArgs(
                        name=f"allow-{ip}",
                        action=pam_app.Action.ALLOW,
                        ip_address_range=str(object=ip),
                    )
                    for ip in self.config.ingress.ip_allow_list or []
                ],
            ),
            registries=(
                [
                    pam_app.RegistryCredentialsArgs(
                        server=self.registry.login_server,
                        username=self.registry.admin_credentials.get("username"),
                        password_secret_ref="registry-secret",
                    )
                ]
                if self.registry
                else None
            ),
            secrets=self._app_secrets(),
        )

    def _app_secrets(self) -> List[pam_app.SecretArgs]:
        return [
            pam_app.SecretArgs(
                name=key,
                value=val,
            )
            for key, val in self.secrets.items()
        ]

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

    def _container_env_vars(self, container) -> List[pam_app.EnvironmentVarArgs]:
        env_args: List[pam_app.EnvironmentVarArgs] = []
        # Env Vars
        env_args.extend(
            [
                pam_app.EnvironmentVarArgs(
                    name=key,
                    value=val,
                )
                for key, val in container.env_vars.items()
            ]
        ) if container.env_vars else None
        # Env Secrets
        env_args.extend(
            [
                pam_app.EnvironmentVarArgs(
                    name=key,
                    secret_ref=val,
                )
                for key, val in container.env_secrets.items()
            ]
        ) if container.env_secrets else None
        return env_args

    def _azure_permissions(self) -> None:
        if self.config.azure_permissions:
            for perm in self.config.azure_permissions:
                iam_assignment(
                    stack=self.stack,
                    config=IamAssignmentConfig(
                        name_prefix=self.app_name,
                        role=perm.role,
                        scope=perm.scope,
                        description=perm.description,
                    ),
                    principal_id=self.app.identity.principal_id,
                    opts=pulumi.ResourceOptions(parent=self.app, delete_before_replace=True),
                )

    def _app_resiliency(self) -> AppResiliency | None:
        if not self.config.resiliency:
            return None

        return AppResiliency(
            resource_name=self.stack.name_for(resource_type=AppResiliency),
            args=AppResiliencyArgs(
                app_name=self.app.name,
                resource_group_name=self.stack.resource_group.name,
                circuit_breaker_policy=CircuitBreakerPolicyArgs(
                    consecutive_errors=self.config.resiliency.circuit_breaker.consecutive_errors,
                    interval_in_seconds=self.config.resiliency.circuit_breaker.interval_in_seconds,
                    max_ejection_percent=self.config.resiliency.circuit_breaker.max_ejection_percent,
                )
                if self.config.resiliency.circuit_breaker
                else None,
                http_connection_pool=HttpConnectionPoolArgs(
                    http1_max_pending_requests=self.config.resiliency.http_connection_pool.http1_max_pending_requests,
                    http2_max_requests=self.config.resiliency.http_connection_pool.http2_max_requests,
                )
                if self.config.resiliency.http_connection_pool
                else None,
                http_retry_policy=HttpRetryPolicyArgs(
                    max_retries=self.config.resiliency.http_retry.max_retries,
                    max_interval_in_milliseconds=self.config.resiliency.http_retry.max_interval_ms,
                    initial_delay_in_milliseconds=self.config.resiliency.http_retry.initial_delay_ms,
                    errors=self.config.resiliency.http_retry.error_types,
                    http_status_codes=self.config.resiliency.http_retry.http_status_codes,
                )
                if self.config.resiliency.http_retry
                else None,
                tcp_connection_pool=TcpConnectionPoolArgs(
                    max_connections=self.config.resiliency.tcp_connection_pool.max_connections,
                )
                if self.config.resiliency.tcp_connection_pool
                else None,
                tcp_retry_policy=TcpRetryPolicyArgs(
                    max_connect_attempts=self.config.resiliency.tcp_retries.max_retries,
                )
                if self.config.resiliency.tcp_retries
                else None,
                timeout_policy=TimeoutPolicyArgs(
                    connection_timeout_in_seconds=self.config.resiliency.timeout.connection_timeout_seconds,
                    response_timeout_in_seconds=self.config.resiliency.timeout.response_timeout_seconds,
                )
                if self.config.resiliency.timeout
                else None,
            ),
            opts=self._opts,
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
                        "default": self.app.configuration.ingress.fqdn.apply(
                            lambda x: f"https://{x}",
                        )
                        if self.config.ingress.protocol == "http"
                        else self.app.configuration.ingress.fqdn,
                        "port": self.config.ingress.exposed_port
                        if (
                            isinstance(self.config.ingress, TcpIngressConfig)
                            and self.config.ingress.exposed_port
                        )
                        else self.config.ingress.target_port,
                        "custom_domains": (
                            self.app.configuration.ingress.custom_domains.apply(
                                lambda x: [f"https://{d.name}" for d in x] if x else []
                            )
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

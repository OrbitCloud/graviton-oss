from typing import Any

import pulumi
from pulumi_azure_native.app import v20240301 as app
from pulumi_azure_native.app.v20231102preview import (
    AppResiliency,
)
from pydantic import BaseModel, ConfigDict, Field, model_validator

from orbitcloud_graviton.az_acr.outputs import AdminUserEnabledRegistryOutput
from orbitcloud_graviton.az_app.scaling import ContainerAppScaleConfig
from orbitcloud_graviton.az_iam.assignment import IamAssignmentConfig, iam_assignment
from orbitcloud_graviton.az_lib.types import AzureIdRef, DictRef, StrRef
from orbitcloud_graviton.pulumi_lib import AzureStack

from ._app_schema import (
    ContainerResourcesConfig,
)
from .ingress import HttpIngressConfig, TcpIngressConfig
from .job_triggers import JobEventTrigger, JobManualTrigger, JobScheduledTrigger
from .outputs import ContainerAppEnvOutput
from .probes import ContainerProbeConfig
from .resiliency import AppResiliencyConfig, app_resiliency


class ContainerConfig(BaseModel):
    name: str
    image: str
    from_public_registry: bool | None = False

    probes: list[ContainerProbeConfig] | None = None
    resources: ContainerResourcesConfig = ContainerResourcesConfig()

    env_vars: dict[str, StrRef | str] | None = None
    env_secrets: dict[str, str] | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ContainerAppBaseConfig(BaseModel):
    name: str | None = None
    environment_output_ref: DictRef
    workload_profile_name: str
    containers: list[ContainerConfig]
    secrets: dict[str, StrRef | str] | None = None
    scaling: ContainerAppScaleConfig | None = ContainerAppScaleConfig()
    resiliency: AppResiliencyConfig | None = None
    log_workspace_id: AzureIdRef | None = None
    registry_output_ref: DictRef | None = None

    azure_permissions: list[IamAssignmentConfig] | None = None

    @model_validator(mode="after")
    def validate_resources(m: "ContainerAppBaseConfig") -> "ContainerAppBaseConfig":
        if m.workload_profile_name == "Consumption":
            for container in m.containers:
                container.resources.validate_consumption_combinations()
        return m

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ContainerAppConfig(ContainerAppBaseConfig):
    ingress: HttpIngressConfig | TcpIngressConfig = Field(..., discriminator="protocol")
    revision_mode: app.ActiveRevisionsMode | None = app.ActiveRevisionsMode.SINGLE


class ContainerAppJobConfig(ContainerAppBaseConfig):
    trigger: JobManualTrigger | JobScheduledTrigger | JobEventTrigger = Field(
        ..., discriminator="trigger_type"
    )


class ContainerApp(pulumi.ComponentResource):
    def __init__(
        self,
        stack: AzureStack,
        config: ContainerAppConfig | ContainerAppJobConfig,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        self.stack: AzureStack = stack
        self.config: ContainerAppConfig | ContainerAppJobConfig = config

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
            resource_type=app.ContainerApp, workload_name=self.config.name
        )

        self.secrets: dict[str, StrRef | str] = self.config.secrets or {}
        self.registry: AdminUserEnabledRegistryOutput | None = self._get_registry()
        self.environment: ContainerAppEnvOutput = self._get_environment()

        self.app: app.ContainerApp | app.Job = (
            self._job() if isinstance(self.config, ContainerAppJobConfig) else self._container_app()
        )

        self.resiliency: AppResiliency | None = app_resiliency(
            app_name=self.app_name,
            stack=self.stack,
            config=self.config.resiliency,
            opts=pulumi.ResourceOptions(parent=self.app),
        )

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

    def _container_app(self) -> app.ContainerApp:
        if not isinstance(self.config, ContainerAppConfig):
            raise ValueError("ContainerAppConfig expected")

        return app.ContainerApp(
            resource_name=self.app_name,
            args=app.ContainerAppArgs(
                container_app_name=self.app_name,
                resource_group_name=self.stack.resource_group.name,
                location=self.stack.location,
                identity=app.ManagedServiceIdentityArgs(type="SystemAssigned"),
                managed_environment_id=str(self.environment.id),
                workload_profile_name=self.config.workload_profile_name,
                template=self._app_template(),
                configuration=self._app_configuration_args(),
            ),
            opts=self._opts,
        )

    def _job(self) -> app.Job:
        if not isinstance(self.config, ContainerAppJobConfig):
            raise ValueError("ContainerAppJobConfig expected")

        return app.Job(
            resource_name=self.app_name,
            args=app.JobArgs(
                job_name=self.app_name,
                resource_group_name=self.stack.resource_group.name,
                location=self.stack.location,
                identity=app.ManagedServiceIdentityArgs(type="SystemAssigned"),
                environment_id=str(self.environment.id),
                workload_profile_name=self.config.workload_profile_name,
                template=self._job_template(),
                configuration=self._job_configuration_args(),
            ),
            opts=self._opts,
        )

    def _containers(self) -> list[app.ContainerArgs]:
        return [
            app.ContainerArgs(
                name=container.name,
                image=pulumi.Output.concat(self.registry.login_server, "/", container.image)
                if self.registry and not container.from_public_registry
                else container.image,
                env=self._container_env_vars(container=container),
                resources=app.ContainerResourcesArgs(
                    cpu=container.resources.cpu,
                    memory=str(container.resources.memory_gb) + "Gi",
                ),
                probes=[probe.args() for probe in container.probes] if container.probes else None,
            )
            for container in self.config.containers
        ]

    def _app_template(self) -> app.TemplateArgs:
        return app.TemplateArgs(
            containers=self._containers(),
            scale=self.config.scaling.args() if self.config.scaling else None,
        )

    def _job_template(self) -> app.JobTemplateArgs:
        return app.JobTemplateArgs(
            containers=self._containers(),
        )

    def _app_configuration_args(self) -> app.ConfigurationArgs:
        if not isinstance(self.config, ContainerAppConfig):
            raise ValueError("ContainerAppConfig expected")

        return app.ConfigurationArgs(
            active_revisions_mode=self.config.revision_mode,
            ingress=self.config.ingress.args(),
            registries=(
                [
                    app.RegistryCredentialsArgs(
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

    def _job_configuration_args(self) -> app.JobConfigurationArgs:
        if not isinstance(self.config, ContainerAppJobConfig):
            raise ValueError("ContainerAppJobConfig expected")

        return app.JobConfigurationArgs(
            replica_timeout=self.config.trigger.replica_timeout_seconds,
            trigger_type=self.config.trigger.trigger_type,
            replica_retry_limit=self.config.trigger.failed_replica_retry_count,
            event_trigger_config=self.config.trigger.event_args()
            if isinstance(self.config.trigger, JobEventTrigger)
            else None,
            manual_trigger_config=self.config.trigger.manual_args()
            if isinstance(self.config.trigger, JobManualTrigger)
            else None,
            schedule_trigger_config=self.config.trigger.schedule_args()
            if isinstance(self.config.trigger, JobScheduledTrigger)
            else None,
            registries=(
                [
                    app.RegistryCredentialsArgs(
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

    def _app_secrets(self) -> list[app.SecretArgs]:
        return [
            app.SecretArgs(
                name=key,
                value=val,
            )
            for key, val in self.secrets.items()
        ]

    def _container_env_vars(self, container) -> list[app.EnvironmentVarArgs]:
        env_args: list[app.EnvironmentVarArgs] = []

        # Env Vars
        env_args.extend(
            [
                app.EnvironmentVarArgs(
                    name=key,
                    value=val,
                )
                for key, val in container.env_vars.items()
            ]
        ) if container.env_vars else None
        # Env Secrets
        env_args.extend(
            [
                app.EnvironmentVarArgs(
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
                        name_prefix=f"{perm.name_prefix}-{self.app_name}"
                        if perm.name_prefix
                        else self.app_name,
                        role=perm.role,
                        scope=perm.scope,
                        description=perm.description,
                    ),
                    principal_id=self.app.identity.principal_id,
                    opts=pulumi.ResourceOptions(parent=self.app, delete_before_replace=True),
                )

    def _outputs(self) -> None:
        self.register_outputs(
            {"app": self.app},
        )

        app_exports: dict[str, Any] = {
            "id": self.app.id,
            "name": self.app.name,
        }

        if isinstance(self.config, ContainerAppConfig):
            app_exports["endpoints"] = {
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
                }
                if isinstance(self.app, app.ContainerApp)
                else {},
            }

        exports = {"app": app_exports}

        self.stack.export(exports=exports)

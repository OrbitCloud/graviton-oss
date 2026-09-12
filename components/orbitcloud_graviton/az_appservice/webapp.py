"""Azure App Service web app component."""

from ipaddress import IPv4Network

import pulumi
from pulumi_azure_native import monitor, web
from pydantic import BaseModel, ConfigDict, Field

from orbitcloud_graviton.az_iam.assignment import IamAssignmentConfig, iam_assignment
from orbitcloud_graviton.az_lib.types import AzureIdRef, StrRef
from orbitcloud_graviton.az_monitor import diagnostic_setting
from orbitcloud_graviton.az_network import PrivateEndpoint, PrivateEndpointConfig
from orbitcloud_graviton.pulumi_lib import AzureStack

LOG_CATEGORIES: list[str] = [
    "AppServiceHTTPLogs",
    "AppServiceConsoleLogs",
    "AppServiceAppLogs",
    "AppServiceAuditLogs",
    "AppServiceIPSecAuditLogs",
    "AppServicePlatformLogs",
]


class WebAppIpRestrictionConfig(BaseModel):
    """A single inbound access rule for the app (or its SCM site)."""

    name: str
    priority: int = Field(default=100, ge=1)
    action: str = "Allow"
    ip_address: StrRef | IPv4Network | str | None = None
    vnet_subnet_id: AzureIdRef | None = None
    service_tag: str | None = None
    description: str | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class WebAppConfig(BaseModel):
    name: str | None = None
    plan_id: AzureIdRef

    # Runtime
    kind: str = "app,linux"
    linux_fx_version: str | None = None
    app_command_line: str | None = None
    always_on: bool = True
    health_check_path: str | None = None
    app_settings: dict[str, StrRef | str] | None = None

    # Security
    https_only: bool = True
    min_tls_version: web.SupportedTlsVersions = web.SupportedTlsVersions.SUPPORTED_TLS_VERSIONS_1_2
    ftps_state: web.FtpsState = web.FtpsState.DISABLED
    http20_enabled: bool = True
    client_affinity_enabled: bool = False
    public_network_access: bool = True
    ip_restrictions: list[WebAppIpRestrictionConfig] | None = None
    ip_restrictions_default_action: str = "Allow"

    # Networking
    vnet_subnet_id: AzureIdRef | None = None
    vnet_route_all_enabled: bool = True
    private_endpoints: list[PrivateEndpointConfig] | None = None

    # Identity
    system_assigned_identity: bool = True
    user_assigned_identity_ids: list[AzureIdRef] | None = None

    log_workspace_id: AzureIdRef | None = None
    azure_permissions: list[IamAssignmentConfig] | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class WebApp(pulumi.ComponentResource):
    """An App Service web app on an existing App Service plan."""

    def __init__(
        self,
        stack: AzureStack,
        config: WebAppConfig,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        self.stack: AzureStack = stack
        self.config: WebAppConfig = config

        super().__init__(
            "Graviton:WebApp",
            name=f"app-{config.name or stack.workload_name}-{stack.env}",
            props=None,
            opts=opts,
        )

        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts1=opts, opts2=pulumi.ResourceOptions(parent=self)
        )

        self.web_app: web.WebApp = self._web_app()
        self.private_endpoints: list[PrivateEndpoint] | None = self._private_endpoints()
        self._azure_permissions()
        self.diagnostic_settings: monitor.DiagnosticSetting | None = self._diagnostic_settings()

        self._outputs()

    @property
    def name(self) -> pulumi.Output[str]:
        return self.web_app.name

    @property
    def id(self) -> pulumi.Output[str]:
        return self.web_app.id

    @property
    def default_hostname(self) -> pulumi.Output[str]:
        return self.web_app.default_host_name

    def _app_name(self) -> str:
        return self.stack.name_for(
            resource_type=web.WebApp,
            workload_name=self.config.name or self.stack.workload_name,
        )

    def _identity(self) -> web.ManagedServiceIdentityArgs | None:
        system: bool = self.config.system_assigned_identity
        user_ids: list[AzureIdRef] | None = self.config.user_assigned_identity_ids

        if system and user_ids:
            identity_type = web.ManagedServiceIdentityType.SYSTEM_ASSIGNED_USER_ASSIGNED
        elif user_ids:
            identity_type = web.ManagedServiceIdentityType.USER_ASSIGNED
        elif system:
            identity_type = web.ManagedServiceIdentityType.SYSTEM_ASSIGNED
        else:
            return None

        return web.ManagedServiceIdentityArgs(
            type=identity_type,
            user_assigned_identities=[str(i) for i in user_ids] if user_ids else None,
        )

    def _app_settings(self) -> list[web.NameValuePairArgs] | None:
        if not self.config.app_settings:
            return None

        return [
            web.NameValuePairArgs(name=key, value=value)
            for key, value in self.config.app_settings.items()
        ]

    def _ip_restrictions(self) -> list[web.IpSecurityRestrictionArgs] | None:
        if not self.config.ip_restrictions:
            return None

        return [
            web.IpSecurityRestrictionArgs(
                name=rule.name,
                priority=rule.priority,
                action=rule.action,
                description=rule.description,
                ip_address=str(rule.ip_address) if rule.ip_address else None,
                vnet_subnet_resource_id=str(rule.vnet_subnet_id) if rule.vnet_subnet_id else None,
                tag="ServiceTag" if rule.service_tag else None,
            )
            for rule in self.config.ip_restrictions
        ]

    def _site_config(self) -> web.SiteConfigArgs:
        return web.SiteConfigArgs(
            linux_fx_version=self.config.linux_fx_version,
            app_command_line=self.config.app_command_line,
            always_on=self.config.always_on,
            health_check_path=self.config.health_check_path,
            app_settings=self._app_settings(),
            http20_enabled=self.config.http20_enabled,
            min_tls_version=self.config.min_tls_version,
            ftps_state=self.config.ftps_state,
            vnet_route_all_enabled=self.config.vnet_route_all_enabled
            if self.config.vnet_subnet_id
            else None,
            ip_security_restrictions=self._ip_restrictions(),
            ip_security_restrictions_default_action=self.config.ip_restrictions_default_action,
            http_logging_enabled=True,
            detailed_error_logging_enabled=True,
        )

    def _web_app(self) -> web.WebApp:
        app_name: str = self._app_name()

        return web.WebApp(
            resource_name=app_name,
            args=web.WebAppArgs(
                name=app_name,
                resource_group_name=self.stack.resource_group.name,
                location=self.stack.resource_group.location,
                tags=self.stack.tags,
                kind=self.config.kind,
                server_farm_id=str(self.config.plan_id),
                # Linux plans require reserved=True.
                reserved="linux" in self.config.kind.lower(),
                https_only=self.config.https_only,
                client_affinity_enabled=self.config.client_affinity_enabled,
                public_network_access="Enabled"
                if self.config.public_network_access
                else "Disabled",
                virtual_network_subnet_id=str(self.config.vnet_subnet_id)
                if self.config.vnet_subnet_id
                else None,
                identity=self._identity(),
                site_config=self._site_config(),
            ),
            opts=self._opts,
        )

    def _private_endpoints(self) -> list[PrivateEndpoint] | None:
        if not self.config.private_endpoints:
            return None

        return [
            PrivateEndpoint(
                stack=self.stack,
                config=pe,
                target_resource=self.web_app,
                opts=self._opts,
            )
            for pe in self.config.private_endpoints
        ]

    def _azure_permissions(self) -> None:
        if not self.config.azure_permissions:
            return

        for perm in self.config.azure_permissions:
            iam_assignment(
                stack=self.stack,
                config=IamAssignmentConfig(
                    name_prefix=f"{perm.name_prefix}-{self.config.name}"
                    if perm.name_prefix
                    else self.config.name,
                    role=perm.role,
                    scope=perm.scope,
                    description=perm.description,
                ),
                principal_id=self.web_app.identity.principal_id,
                opts=pulumi.ResourceOptions(parent=self.web_app, delete_before_replace=True),
            )

    def _diagnostic_settings(self) -> monitor.DiagnosticSetting | None:
        if not self.config.log_workspace_id:
            return None

        return diagnostic_setting(
            resource=self.web_app,
            log_workspace_id=str(self.config.log_workspace_id),
            metric_categories=["AllMetrics"],
            log_categories=LOG_CATEGORIES,
            opts=pulumi.ResourceOptions(parent=self.web_app),
        )

    def _outputs(self) -> None:
        self.register_outputs({"web_app": self.web_app})

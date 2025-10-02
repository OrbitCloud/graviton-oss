from uuid import UUID

import pulumi
from pulumi_azure_native import monitor, sql
from pulumi_azure_native.managedidentity import UserAssignedIdentity
from pulumi_azure_native.sql import (
    JobAgent,
    JobAgentArgs,
    JobAgentIdentityArgs,
    JobAgentIdentityType,
    JobTargetArgs,
    JobTargetGroup,
    JobTargetGroupArgs,
    JobTargetType,
    SkuArgs,
)
from pulumi_random import RandomPassword, RandomPasswordArgs
from pydantic import BaseModel, ConfigDict

from orbitcloud_graviton.az_iam import user_assigned_id
from orbitcloud_graviton.az_lib.helpers import fmt_name
from orbitcloud_graviton.az_lib.types import AzureIdRef
from orbitcloud_graviton.az_monitor import diagnostic_setting
from orbitcloud_graviton.az_network import PrivateEndpoint, PrivateEndpointConfig
from orbitcloud_graviton.az_network.types import PublicIpv4FirewallRule
from orbitcloud_graviton.pulumi_lib import AzureStack

from .database import SqlDatabase, SqlDatabaseConfig, SqlDatabaseSku


class SqlServerEntraAdmin(BaseModel):
    principal_type: sql.PrincipalType
    sid: UUID
    login_name: str


class SqlServerAdmin(BaseModel):
    admin_name: str = "azuresa"
    admin_password: str | None = None

    def password(
        self,
        parent: pulumi.ComponentResource | None = None,
    ) -> pulumi.Output[str] | str:
        if self.admin_password is None:
            return RandomPassword(
                resource_name=f"sql-admin-password-{self.admin_name}",
                args=RandomPasswordArgs(
                    length=32,
                    special=True,
                    upper=True,
                    lower=True,
                    numeric=True,
                ),
                opts=pulumi.ResourceOptions(parent=parent),
            ).result

        return self.admin_password


class SqlServerElasticPool(BaseModel):
    enabled: bool | None = False
    max_size_gb: int = 32
    sku: SqlDatabaseSku | None = None


class SqlServerConfig(BaseModel):
    name: str | None = None

    azure_ad_only_authentication: bool = True
    entra_admin: SqlServerEntraAdmin
    administrator: SqlServerAdmin = SqlServerAdmin()
    elastic_pool: SqlServerElasticPool | None = None

    job_agent_enabled: bool | None = False

    public_network_access: sql.ServerNetworkAccessFlag = sql.ServerNetworkAccessFlag.DISABLED
    allowed_subnet_ids: list[AzureIdRef] | None = None
    allowed_public_networks: list[PublicIpv4FirewallRule] | None = None
    allow_azure_services: bool = False

    dns_alias: str | None = None

    private_endpoints: list[PrivateEndpointConfig] | None = None

    log_workspace_id: AzureIdRef | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class SqlServer(pulumi.ComponentResource):
    def __init__(
        self,
        stack: AzureStack,
        config: SqlServerConfig,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        self.stack: AzureStack = stack
        self.config: SqlServerConfig = config

        super().__init__(
            "Graviton:SqlServer",
            name=f"sql-{stack.workload_name}-{stack.env}",
            props=None,
            opts=opts,
        )

        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts1=opts, opts2=pulumi.ResourceOptions(parent=self)
        )

        self.server: sql.Server = self._server()
        self.allowed_subnets: list[sql.VirtualNetworkRule] = self._allowed_subnets()
        self.allowed_public_networks: list[sql.FirewallRule] = self._allowed_public_networks()
        self.allow_azure_services: sql.FirewallRule | None = self._allow_azure_services()
        self.dns_alias: sql.ServerDnsAlias | None = self._dns_alias()
        self.elastic_pool: sql.ElasticPool | None = self._elastic_pool()
        self.private_endpoints: list[PrivateEndpoint] | None = self._private_endpoints()
        self.diagnostic_settings: monitor.DiagnosticSetting | None = self._diagnostic_settings()
        self.elastic_job_agent: JobAgent | None = self._elastic_job_agent()

        self._outputs()

    def _server(self) -> sql.Server:
        return sql.Server(
            resource_name=self.stack.name_for(
                resource_type=sql.Server, workload_name=self.config.name
            ),
            args=sql.ServerArgs(
                resource_group_name=self.stack.resource_group.name,
                server_name=self.stack.name_for(
                    resource_type=sql.Server, workload_name=self.config.name
                ),
                identity=sql.ResourceIdentityArgs(type=sql.IdentityType.SYSTEM_ASSIGNED),
                minimal_tls_version="1.2",
                public_network_access=self.config.public_network_access,
                administrators=sql.ServerExternalAdministratorArgs(
                    azure_ad_only_authentication=self.config.azure_ad_only_authentication,
                    administrator_type=sql.AdministratorType.ACTIVE_DIRECTORY,
                    login=self.config.entra_admin.login_name,
                    tenant_id=str(self.stack.tenant_id),
                    principal_type=self.config.entra_admin.principal_type,
                    sid=str(self.config.entra_admin.sid),
                ),
                administrator_login=self.config.administrator.admin_name
                if not self.config.azure_ad_only_authentication
                else None,
                administrator_login_password=self.config.administrator.password(parent=self)
                if not self.config.azure_ad_only_authentication
                else None,
            ),
            opts=self._opts,
        )

    def _elastic_pool(self) -> sql.ElasticPool | None:
        if not self.config.elastic_pool:
            return None

        return sql.ElasticPool(
            resource_name=self.stack.name_for(
                resource_type=sql.ElasticPool, workload_name=self.config.name
            ),
            args=sql.ElasticPoolArgs(
                resource_group_name=self.stack.resource_group.name,
                server_name=self.server.name,
                max_size_bytes=self.config.elastic_pool.max_size_gb * 1024 * 1024 * 1024,
                elastic_pool_name=self.stack.name_for(
                    resource_type=sql.ElasticPool, workload_name=self.config.name
                ),
            ),
            opts=pulumi.ResourceOptions.merge(
                opts1=self._opts,
                opts2=pulumi.ResourceOptions(parent=self.server),
            ),
        )

    def _allowed_subnets(self) -> list[sql.VirtualNetworkRule]:
        return [
            sql.VirtualNetworkRule(
                resource_name=self.stack.name_for(resource_type=sql.VirtualNetworkRule),
                args=sql.VirtualNetworkRuleArgs(
                    server_name=self.server.name,
                    resource_group_name=self.stack.resource_group.name,
                    virtual_network_subnet_id=subnet_id,
                ),
                opts=pulumi.ResourceOptions.merge(
                    opts1=self._opts,
                    opts2=pulumi.ResourceOptions(parent=self.server, delete_before_replace=True),
                ),
            )
            for subnet_id in self.config.allowed_subnet_ids or []
        ]

    def _allow_azure_services(self) -> sql.FirewallRule | None:
        if self.config.allow_azure_services:
            return sql.FirewallRule(
                resource_name=self.stack.name_for(
                    resource_type=sql.FirewallRule, workload_name="AzureServices"
                ),
                args=sql.FirewallRuleArgs(
                    firewall_rule_name="AzureServices",
                    server_name=self.server.name,
                    resource_group_name=self.stack.resource_group.name,
                    start_ip_address="0.0.0.0",
                    end_ip_address="0.0.0.0",
                ),
                opts=pulumi.ResourceOptions.merge(
                    opts1=self._opts,
                    opts2=pulumi.ResourceOptions(parent=self.server, delete_before_replace=True),
                ),
            )

    def _allowed_public_networks(self) -> list[sql.FirewallRule]:
        return [
            sql.FirewallRule(
                resource_name=self.stack.name_for(
                    resource_type=sql.FirewallRule, workload_name=fmt_name(public_network.name)
                ),
                args=sql.FirewallRuleArgs(
                    firewall_rule_name=public_network.name,
                    server_name=self.server.name,
                    resource_group_name=self.stack.resource_group.name,
                    start_ip_address=public_network.first_ip,
                    end_ip_address=public_network.last_ip,
                ),
                opts=pulumi.ResourceOptions.merge(
                    opts1=self._opts,
                    opts2=pulumi.ResourceOptions(parent=self.server, delete_before_replace=True),
                ),
            )
            for public_network in self.config.allowed_public_networks or []
        ]

    def _dns_alias(self) -> sql.ServerDnsAlias | None:
        return (
            sql.ServerDnsAlias(
                resource_name=self.stack.name_for(resource_type=sql.ServerDnsAlias),
                args=sql.ServerDnsAliasArgs(
                    server_name=self.server.name,
                    resource_group_name=self.stack.resource_group.name,
                    dns_alias_name=self.config.dns_alias,
                ),
                opts=pulumi.ResourceOptions(parent=self.server),
            )
            if self.config.dns_alias
            else None
        )

    def _private_endpoints(self) -> list[PrivateEndpoint] | None:
        if self.config.private_endpoints:
            return [
                PrivateEndpoint(
                    stack=self.stack,
                    config=endpoint,
                    target_resource=self.server,
                    opts=pulumi.ResourceOptions.merge(
                        self._opts, pulumi.ResourceOptions(parent=self.server)
                    ),
                )
                for endpoint in self.config.private_endpoints
            ]

    def _elastic_job_agent(self) -> JobAgent | None:
        if self.config.job_agent_enabled:
            agent_db = SqlDatabase(
                stack=self.stack,
                server_name=self.server.name,
                config=SqlDatabaseConfig(
                    name="jobagent",
                    log_workspace_id=self.config.log_workspace_id,
                    elastic_pool_id=self.elastic_pool.id if self.elastic_pool else None,
                ),
                opts=self._opts,
            )

            identity: UserAssignedIdentity = user_assigned_id(
                name="sqljobagent",
                stack=self.stack,
                opts=self._opts,
            )

            ja = JobAgent(
                resource_name=self.stack.name_for(
                    resource_type=JobAgent, workload_name=self.config.name
                ),
                args=JobAgentArgs(
                    database_id=agent_db.database.id,
                    resource_group_name=self.stack.resource_group.name,
                    server_name=self.server.name,
                    identity=JobAgentIdentityArgs(
                        type=JobAgentIdentityType.USER_ASSIGNED,
                        user_assigned_identities=[identity.id],
                    ),
                    sku=SkuArgs(
                        name="JA100",
                    ),
                ),
                opts=self._opts,
            )

            JobTargetGroup(
                resource_name=self.stack.name_for(
                    resource_type=JobTargetGroup, workload_name=self.config.name
                ),
                args=JobTargetGroupArgs(
                    job_agent_name=ja.name,
                    resource_group_name=self.stack.resource_group.name,
                    server_name=self.server.name,
                    members=[
                        JobTargetArgs(
                            type=JobTargetType.SQL_ELASTIC_POOL
                            if self.elastic_pool
                            else JobTargetType.SQL_SERVER,
                            server_name=self.server.name,
                            elastic_pool_name=self.elastic_pool.name if self.elastic_pool else None,
                        )
                    ],
                ),
                opts=self._opts,
            )

            return ja

    def _diagnostic_settings(self) -> monitor.DiagnosticSetting | None:
        if self.config.log_workspace_id and self.elastic_pool:
            return diagnostic_setting(
                resource=self.elastic_pool,
                log_workspace_id=self.config.log_workspace_id,
                metric_categories=["Basic", "InstanceAndAppAdvanced"],
                opts=pulumi.ResourceOptions(parent=self.elastic_pool),
            )

    def _outputs(self) -> None:
        self.register_outputs(
            outputs={"server": self.server},
        )

        self.stack.export(
            exports={
                "server": {
                    "id": self.server.id,
                    "name": self.server.name,
                    "allowed_subnets": [subnet.id for subnet in self.allowed_subnets],
                    "allowed_public_networks": [
                        {
                            "name": "rule.name",
                            "first_ip": rule.start_ip_address,
                            "last_ip": rule.end_ip_address,
                        }
                        for rule in self.allowed_public_networks
                    ],
                    "endpoints": {
                        "public": self.server.fully_qualified_domain_name,
                        "public_alias": self.dns_alias.azure_dns_record if self.dns_alias else None,
                    },
                }
            }
        )

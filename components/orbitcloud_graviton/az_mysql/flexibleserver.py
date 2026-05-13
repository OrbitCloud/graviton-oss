import logging

import pulumi
from pulumi_azure_native import dbformysql as mysql
from pulumi_azure_native import monitor
from pulumi_random import RandomPassword, RandomPasswordArgs
from pydantic import BaseModel, ConfigDict, Field, model_validator

from orbitcloud_graviton.az_lib.helpers import fmt_name
from orbitcloud_graviton.az_lib.types import AzureIdRef
from orbitcloud_graviton.az_monitor import diagnostic_setting
from orbitcloud_graviton.az_network.types import PublicIpv4FirewallRule
from orbitcloud_graviton.pulumi_lib import AzureStack, EntraStack

logger = logging.getLogger(__name__)


class MysqlAuthConfig(BaseModel):
    admin_username: str = "cloudsa"
    admin_password: str | None = None

    entra_auth: bool = True

    model_config = ConfigDict(extra="forbid")


class MysqlNetworkConfig(BaseModel):
    subnet_id: AzureIdRef
    private_dns_zone_id: AzureIdRef

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class MysqlStorageConfig(BaseModel):
    storage_size_gb: int = Field(default=32, ge=20, le=16384)
    auto_grow: mysql.EnableStatusEnum = mysql.EnableStatusEnum.DISABLED
    auto_io_scaling: mysql.EnableStatusEnum = mysql.EnableStatusEnum.ENABLED
    iops: int | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class MysqlBackupConfig(BaseModel):
    geo_redundant: mysql.EnableStatusEnum = mysql.EnableStatusEnum.DISABLED
    retention_days: int = 7

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class MysqlSku(BaseModel):
    name: str = "Standard_B1ms"
    tier: mysql.ServerSkuTier = mysql.ServerSkuTier.BURSTABLE

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class MysqlHAConfig(BaseModel):
    mode: mysql.HighAvailabilityMode = mysql.HighAvailabilityMode.DISABLED
    standby_availability_zone: str | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class MysqlMaintenanceConfig(BaseModel):
    day_of_week: int = Field(default=0, ge=0, le=6)
    start_hour: int = Field(default=0, ge=0, le=23)
    start_minute: int = Field(default=0, ge=0, le=59)

    model_config = ConfigDict(extra="forbid")


class MysqlCreateMode(BaseModel):
    mode: mysql.CreateMode | None = None
    source_server_id: AzureIdRef | None = None
    restore_point_in_time: str | None = None

    @model_validator(mode="after")
    def validate_create_mode(self) -> "MysqlCreateMode":
        requires_source = (
            mysql.CreateMode.POINT_IN_TIME_RESTORE,
            mysql.CreateMode.GEO_RESTORE,
            mysql.CreateMode.REPLICA,
        )
        if self.mode in requires_source and not self.source_server_id:
            raise ValueError(f"source_server_id is required when mode is {self.mode}")

        if self.mode == mysql.CreateMode.POINT_IN_TIME_RESTORE and not self.restore_point_in_time:
            raise ValueError("restore_point_in_time is required when mode is POINT_IN_TIME_RESTORE")

        return self

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class MysqlDatabaseConfig(BaseModel):
    name: str
    charset: str = "utf8mb4"
    collation: str = "utf8mb4_unicode_ci"

    model_config = ConfigDict(extra="forbid")


class MysqlFlexibleServerConfig(BaseModel):
    server_name: str | None = None
    server_version: str = "8.4"
    authentication: MysqlAuthConfig = MysqlAuthConfig()
    network: MysqlNetworkConfig | None = None
    sku: MysqlSku = MysqlSku()
    storage: MysqlStorageConfig = MysqlStorageConfig()
    backups: MysqlBackupConfig = MysqlBackupConfig()
    high_availability: MysqlHAConfig = MysqlHAConfig()
    maintenance: MysqlMaintenanceConfig | None = None
    create_mode: MysqlCreateMode = MysqlCreateMode()
    zone: str | None = None

    databases: list[MysqlDatabaseConfig] | None = None
    server_params: dict[str, str] | None = None

    allowed_public_networks: list[PublicIpv4FirewallRule] | None = None
    allow_azure_services: bool = False

    log_workspace_id: AzureIdRef | None = None

    @model_validator(mode="after")
    def validate_network_firewall_exclusive(
        self,
    ) -> "MysqlFlexibleServerConfig":
        if self.network and (self.allowed_public_networks or self.allow_azure_services):
            raise ValueError(
                "VNet integration (network) and firewall rules "
                "(allowed_public_networks / allow_azure_services) are mutually exclusive"
            )
        return self

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class MysqlFlexibleServer(pulumi.ComponentResource):
    def __init__(
        self,
        stack: AzureStack,
        entra_config: EntraStack,
        config: MysqlFlexibleServerConfig,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        self.stack: AzureStack = stack
        self.config: MysqlFlexibleServerConfig = config
        self.entra_config: EntraStack = entra_config

        super().__init__(
            "Graviton:MysqlFlexibleServer",
            name=f"mysql-{stack.workload_name}-{stack.env}",
            props=None,
            opts=opts,
        )

        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts1=opts, opts2=pulumi.ResourceOptions(parent=self)
        )
        self.admin_password: str | pulumi.Output[str] = (
            self.config.authentication.admin_password or self._random_admin_password().result
        )

        self.server: mysql.Server = self._server()
        self.admins = self._server_admin()
        self.databases: list[mysql.Database] = self._databases()
        self.firewall_rules: list[mysql.FirewallRule] = self._firewall_rules()
        self.azure_services_rule: mysql.FirewallRule | None = self._allow_azure_services()
        self._diagnostic_settings()
        self.server_params: list[mysql.Configuration] | None = self._server_params()

        self._outputs()

    def _server(self) -> mysql.Server:
        public_access = mysql.EnableStatusEnum.DISABLED
        if not self.config.network:
            public_access = mysql.EnableStatusEnum.ENABLED

        args = mysql.ServerArgs(
            resource_group_name=self.stack.resource_group.name,
            server_name=self.config.server_name or self.stack.name_for(resource_type=mysql.Server),
            location=self.stack.location,
            # SKU
            sku=mysql.MySQLServerSkuArgs(
                name=self.config.sku.name,
                tier=self.config.sku.tier,
            ),
            high_availability=mysql.HighAvailabilityArgs(
                mode=self.config.high_availability.mode,
                standby_availability_zone=self.config.high_availability.standby_availability_zone,
            ),
            version=self.config.server_version,
            # Storage
            availability_zone=self.config.zone,
            storage=mysql.StorageArgs(
                auto_grow=self.config.storage.auto_grow,
                auto_io_scaling=self.config.storage.auto_io_scaling,
                storage_size_gb=self.config.storage.storage_size_gb,
                iops=self.config.storage.iops,
            ),
            # Authentication
            administrator_login=self.config.authentication.admin_username,
            administrator_login_password=self.admin_password,
            # Networking
            network=mysql.NetworkArgs(
                delegated_subnet_resource_id=self.config.network.subnet_id
                if self.config.network
                else None,
                private_dns_zone_resource_id=self.config.network.private_dns_zone_id
                if self.config.network
                else None,
                public_network_access=public_access,
            ),
            # Backups
            backup=mysql.BackupArgs(
                geo_redundant_backup=self.config.backups.geo_redundant,
                backup_retention_days=self.config.backups.retention_days,
            ),
            maintenance_window=mysql.MaintenanceWindowArgs(
                custom_window="Enabled",
                day_of_week=self.config.maintenance.day_of_week,
                start_hour=self.config.maintenance.start_hour,
                start_minute=self.config.maintenance.start_minute,
            )
            if self.config.maintenance
            else None,
            # Create mode
            create_mode=self.config.create_mode.mode,
            source_server_resource_id=self.config.create_mode.source_server_id,
            restore_point_in_time=self.config.create_mode.restore_point_in_time,
            data_encryption=mysql.DataEncryptionArgs(
                type=mysql.DataEncryptionType.SYSTEM_MANAGED,
            ),
            replication_role=mysql.ReplicationRole.NONE,
        )

        return mysql.Server(
            resource_name=self.stack.name_for(resource_type=mysql.Server),
            args=args,
            opts=self._opts,
        )

    def _random_admin_password(self) -> RandomPassword:
        return RandomPassword(
            resource_name=self.stack.name_for(
                resource_type=RandomPassword,
                workload_name=f"{self.stack.workload_name}-mysql-admin-pwd",
            ),
            args=RandomPasswordArgs(
                length=24,
                special=True,
                upper=True,
                lower=True,
                numeric=True,
            ),
            opts=self._opts,
        )

    def _server_admin(self) -> mysql.AzureADAdministrator | None:
        if not self.config.authentication.entra_auth:
            return None

        if self.stack.azure_environment:
            return mysql.AzureADAdministrator(
                resource_name=self.stack.name_for(
                    resource_type=mysql.AzureADAdministrator,
                    workload_name=self.stack.azure_environment.pulumi_esc_app.name,
                ),
                args=mysql.AzureADAdministratorArgs(
                    resource_group_name=self.stack.resource_group.name,
                    server_name=self.server.name,
                    tenant_id=str(self.entra_config.tenant_id),
                    administrator_type=mysql.AdministratorType.ACTIVE_DIRECTORY,
                    sid=str(
                        self.stack.azure_environment.pulumi_esc_app.service_principal_object_id
                    ),
                    login=self.stack.azure_environment.pulumi_esc_app.name,
                    identity_resource_id=None,
                ),
                opts=pulumi.ResourceOptions(parent=self.server),
            )

        logger.warning(
            "Entra authentication is enabled but azure_environment is not set. "
            "No Entra admin will be configured for the MySQL server."
        )
        return None

    def _databases(self) -> list[mysql.Database]:
        if not self.config.databases:
            return []

        return [
            mysql.Database(
                resource_name=self.stack.name_for(
                    resource_type=mysql.Database, workload_name=db.name
                ),
                args=mysql.DatabaseArgs(
                    resource_group_name=self.stack.resource_group.name,
                    server_name=self.server.name,
                    database_name=db.name,
                    charset=db.charset,
                    collation=db.collation,
                ),
                opts=pulumi.ResourceOptions(parent=self.server),
            )
            for db in self.config.databases
        ]

    def _firewall_rules(self) -> list[mysql.FirewallRule]:
        if not self.config.allowed_public_networks:
            return []

        return [
            mysql.FirewallRule(
                resource_name=self.stack.name_for(
                    resource_type=mysql.FirewallRule, workload_name=fmt_name(rule.name)
                ),
                args=mysql.FirewallRuleArgs(
                    firewall_rule_name=rule.name,
                    server_name=self.server.name,
                    resource_group_name=self.stack.resource_group.name,
                    start_ip_address=rule.first_ip,
                    end_ip_address=rule.last_ip,
                ),
                opts=pulumi.ResourceOptions.merge(
                    opts1=self._opts,
                    opts2=pulumi.ResourceOptions(parent=self.server, delete_before_replace=True),
                ),
            )
            for rule in self.config.allowed_public_networks
        ]

    def _allow_azure_services(self) -> mysql.FirewallRule | None:
        if not self.config.allow_azure_services:
            return None

        return mysql.FirewallRule(
            resource_name=self.stack.name_for(
                resource_type=mysql.FirewallRule, workload_name="AzureServices"
            ),
            args=mysql.FirewallRuleArgs(
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

    def _server_params(self) -> list[mysql.Configuration] | None:
        if not self.config.server_params:
            return None

        return [
            mysql.Configuration(
                resource_name=self.stack.name_for(
                    mysql.Configuration,
                    workload_name=k.replace("_", "-").replace(".", "-"),
                ),
                args=mysql.ConfigurationArgs(
                    resource_group_name=self.stack.resource_group.name,
                    server_name=self.server.name,
                    source="user-override",
                    configuration_name=k,
                    value=v,
                ),
                opts=pulumi.ResourceOptions(parent=self.server),
            )
            for k, v in self.config.server_params.items()
        ]

    def _diagnostic_settings(self) -> monitor.DiagnosticSetting | None:
        if self.config.log_workspace_id:
            return diagnostic_setting(
                resource=self.server,
                log_workspace_id=self.config.log_workspace_id,
                metric_categories=[
                    "AllMetrics",
                ],
                log_categories=[
                    "MySqlAuditLogs",
                    "MySqlSlowLogs",
                ],
                opts=pulumi.ResourceOptions(parent=self.server),
            )
        return None

    def _outputs(self) -> None:
        self.register_outputs(
            outputs={"server": self.server},
        )

        self.stack.export(
            exports={
                "mysql": {
                    "id": self.server.id,
                    "name": self.server.name,
                    "endpoint": self.server.fully_qualified_domain_name,
                    "admin": {
                        "username": self.config.authentication.admin_username,
                        "password": self.admin_password,
                    },
                }
            }
        )

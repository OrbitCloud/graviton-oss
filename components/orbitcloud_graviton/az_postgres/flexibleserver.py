from uuid import UUID

import pulumi
from pulumi_azure_native import insights
from pulumi_azure_native.dbforpostgresql import (
    v20231201preview as postgres,  # Required for storage disk configurations
)
from pulumi_random import RandomPassword, RandomPasswordArgs
from pydantic import BaseModel, ConfigDict, Field, model_validator

from orbitcloud_graviton.az_lib.types import AzureIdRef
from orbitcloud_graviton.az_monitor import diagnostic_setting
from orbitcloud_graviton.pulumi_lib import AzureStack, EntraStack


class PostgresAuthConfig(BaseModel):
    admin_username: str = "cloudsa"
    admin_password: str | None = None

    entra_auth: postgres.ActiveDirectoryAuthEnum = postgres.ActiveDirectoryAuthEnum.ENABLED
    entra_admins: list[UUID] | None = None
    postgres_auth: postgres.PasswordAuthEnum = postgres.PasswordAuthEnum.ENABLED

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class PostgresBackupConfig(BaseModel):
    geo_redundant: postgres.GeoRedundantBackupEnum = postgres.GeoRedundantBackupEnum.DISABLED
    retention_days: int = 7

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class PostgresSku(BaseModel):
    name: str = "Standard_B1ms"
    tier: postgres.SkuTier = postgres.SkuTier.BURSTABLE

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class PostgresCreateMode(BaseModel):
    mode: postgres.CreateMode | None = None
    source_server_id: AzureIdRef | None = None

    @model_validator(mode="after")
    def validate_source_server_id(m: "PostgresCreateMode") -> "PostgresCreateMode":
        if (
            m.mode
            in (
                postgres.CreateMode.POINT_IN_TIME_RESTORE,
                postgres.CreateMode.GEO_RESTORE,
                postgres.CreateMode.REPLICA,
            )
            and not m.source_server_id
        ):
            raise ValueError(f"source_server_id is required when mode is {m.mode}")

        return m

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class PostgresMaintenanceConfig(BaseModel):
    day_of_week: int | None = Field(default=0, ge=0, le=6)
    start_hour: int | None = Field(default=0, ge=0, le=23)
    start_minute: int | None = Field(default=0, ge=0, le=59)

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class PostgresStorageConfig(BaseModel):
    auto_growth: postgres.StorageAutoGrow | None = postgres.StorageAutoGrow.ENABLED
    storage_size_gb: int | None = Field(default=32, ge=32, le=65536)
    tier: postgres.AzureManagedDiskPerformanceTiers | None = None
    storage_type: postgres.StorageType = postgres.StorageType.PREMIUM_LRS
    iops: int | None = None
    throughput: int | None = Field(default=None, ge=125, le=750)

    @model_validator(mode="after")
    def validate_iops_throughput(m: "PostgresStorageConfig") -> "PostgresStorageConfig":
        if m.storage_type == postgres.StorageType.PREMIUM_V2_LRS and (
            not m.iops or not m.throughput
        ):
            raise ValueError("iops and throughput are required when storage_type is PREMIUM_V2_LRS")
        return m

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class PostgresNetworkConfig(BaseModel):
    subnet_id: AzureIdRef
    private_dns_zone_id: AzureIdRef

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class PostgresFlexibleServerConfig(BaseModel):
    server_name: str | None = None
    server_version: postgres.ServerVersion = postgres.ServerVersion.SERVER_VERSION_16
    authentication: PostgresAuthConfig = PostgresAuthConfig()
    network: PostgresNetworkConfig | None = None
    sku: PostgresSku = PostgresSku()
    storage: PostgresStorageConfig = PostgresStorageConfig()
    backups: PostgresBackupConfig = PostgresBackupConfig()
    server_params: dict[str, str] | None = None
    create_mode: PostgresCreateMode = PostgresCreateMode()
    maintenance: PostgresMaintenanceConfig | None = None
    zone: str | None = None

    high_availability: postgres.HighAvailabilityMode = postgres.HighAvailabilityMode.DISABLED

    log_workspace_id: AzureIdRef | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class PostgresFlexibleServer(pulumi.ComponentResource):
    def __init__(
        self,
        stack: AzureStack,
        entra_config: EntraStack,
        config: PostgresFlexibleServerConfig,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        self.stack: AzureStack = stack
        self.config: PostgresFlexibleServerConfig = config
        self.entra_config: EntraStack = entra_config

        super().__init__(
            "Graviton:PostgresFlexibleServer",
            name=f"psql-{stack.workload_name}-{stack.env}",
            props=None,
            opts=opts,
        )

        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts1=opts, opts2=pulumi.ResourceOptions(parent=self)
        )
        self.admin_password: str | pulumi.Output[str] = (
            self.config.authentication.admin_password or self._random_admin_password().result
        )

        self.server: postgres.Server = self._server()
        self.admins = self._server_admin()
        self._diagnostic_settings()
        self.server_params: list[postgres.Configuration] | None = self._server_params()

        self._outputs()

    def _server(self) -> postgres.Server:
        args = postgres.ServerArgs(
            resource_group_name=self.stack.resource_group.name,
            server_name=self.config.server_name
            or self.stack.name_for(resource_type=postgres.Server),
            location=self.stack.location,
            # SKU
            sku=postgres.SkuArgs(
                name=self.config.sku.name,
                tier=self.config.sku.tier,
            ),
            high_availability=postgres.HighAvailabilityArgs(
                mode=self.config.high_availability,
            ),
            version=self.config.server_version,
            # Storage
            availability_zone=self.config.zone,
            storage=postgres.StorageArgs(
                auto_grow=self.config.storage.auto_growth,
                storage_size_gb=self.config.storage.storage_size_gb,
                tier=self.config.storage.tier,
                iops=self.config.storage.iops,
                # throughput=self.config.storage.throughput,
            ),
            # Authentication
            administrator_login=self.config.authentication.admin_username,
            administrator_login_password=self.admin_password,
            auth_config=postgres.AuthConfigArgs(
                active_directory_auth=self.config.authentication.entra_auth,
                password_auth=self.config.authentication.postgres_auth,
                tenant_id=str(object=self.entra_config.tenant_id),
            ),
            # Networking
            network=postgres.NetworkArgs(
                delegated_subnet_resource_id=self.config.network.subnet_id
                if self.config.network
                else None,
                private_dns_zone_arm_resource_id=self.config.network.private_dns_zone_id
                if self.config.network
                else None,
                public_network_access=postgres.ServerPublicNetworkAccessState.DISABLED,
            ),
            # Backups
            backup=postgres.BackupArgs(
                geo_redundant_backup=self.config.backups.geo_redundant,
                backup_retention_days=self.config.backups.retention_days,
            ),
            maintenance_window=postgres.MaintenanceWindowArgs(
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
            data_encryption=postgres.DataEncryptionArgs(
                type=postgres.ArmServerKeyType.SYSTEM_MANAGED,
            ),
            replication_role=postgres.ReplicationRole.PRIMARY,
        )

        return postgres.Server(
            resource_name=self.stack.name_for(resource_type=postgres.Server),
            args=args,
            opts=self._opts,
        )

    def _random_admin_password(self) -> RandomPassword:
        return RandomPassword(
            resource_name=self.stack.name_for(
                resource_type=RandomPassword,
                workload_name=f"{self.stack.workload_name}-psql-admin-pwd",
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

    def _server_admin(self) -> postgres.Administrator | None:
        if self.stack.azure_environment:
            return postgres.Administrator(
                resource_name=self.stack.name_for(
                    resource_type=postgres.Administrator,
                    workload_name=self.stack.azure_environment.pulumi_esc_app.name,
                ),
                args=postgres.AdministratorArgs(
                    resource_group_name=self.stack.resource_group.name,
                    server_name=self.server.name,
                    tenant_id=str(self.stack.tenant_id),
                    principal_type=postgres.PrincipalType.SERVICE_PRINCIPAL,
                    object_id=str(
                        self.stack.azure_environment.pulumi_esc_app.service_principal_object_id
                    ),
                    principal_name=self.stack.azure_environment.pulumi_esc_app.name,
                ),
                opts=pulumi.ResourceOptions(parent=self.server),
            )

    def _server_params(self) -> list[postgres.Configuration] | None:
        return (
            [
                postgres.Configuration(
                    resource_name=self.stack.name_for(
                        postgres.Configuration, workload_name=k.replace("_", "-").replace(".", "-")
                    ),
                    args=postgres.ConfigurationArgs(
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
            if self.config.server_params
            else None
        )

    def _diagnostic_settings(self) -> insights.DiagnosticSetting | None:
        if self.config.log_workspace_id:
            return diagnostic_setting(
                resource=self.server,
                log_workspace_id=self.config.log_workspace_id,
                metric_categories=[
                    "AllMetrics",
                ],
                log_categories=[
                    "PostgreSQLLogs",
                    "PostgreSQLFlexSessions",
                    "PostgreSQLFlexQueryStoreRuntime",
                    "PostgreSQLFlexQueryStoreWaitStats",
                    "PostgreSQLFlexDatabaseXacts",
                    "PostgreSQLFlexTableStats",
                ],
                opts=pulumi.ResourceOptions(parent=self.server),
            )

    def _outputs(self) -> None:
        self.register_outputs(
            outputs={"server": self.server},
        )

        self.stack.export(
            exports={
                "postgres": {
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

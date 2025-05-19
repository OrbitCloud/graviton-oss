from typing import Literal

import pulumi
from pulumi_azure_native import monitor, sql
from pydantic import BaseModel, ConfigDict

from orbitcloud_graviton.az_lib.types import AzureIdRef, StrRef
from orbitcloud_graviton.az_monitor import diagnostic_setting
from orbitcloud_graviton.pulumi_lib import AzureStack


class SqlDatabaseSku(BaseModel):
    # Check available editions with:
    # az sql db list-editions --location northeurope --output table
    name: str = "S0"
    tier: Literal["Basic", "Standard", "Premium", "GeneralPurpose", "Hyperscale"] = "Standard"


class SqlDatabaseConfig(BaseModel):
    name: str | None = None
    elastic_pool_id: AzureIdRef | None = None

    create_mode: sql.CreateMode = sql.CreateMode.DEFAULT
    source_database_id: AzureIdRef | None = None

    max_size_mb: int | None = None
    collation: sql.CatalogCollationType = sql.CatalogCollationType.SQ_L_LATIN1_GENERAL_CP1_C_I_AS

    zone_redundant: bool | None = False
    backup_redundancy: sql.BackupStorageRedundancy = sql.BackupStorageRedundancy.LOCAL

    sku: SqlDatabaseSku | None = None

    log_workspace_id: AzureIdRef | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class SqlDatabase(pulumi.ComponentResource):
    def __init__(
        self,
        stack: AzureStack,
        config: SqlDatabaseConfig,
        server_name: StrRef,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        self.stack: AzureStack = stack
        self.config: SqlDatabaseConfig = config

        super().__init__(
            "Graviton:SqlDatabase",
            name=f"sqldb-{self.config.name}-{stack.env}",
            props=None,
            opts=opts,
        )

        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts1=opts, opts2=pulumi.ResourceOptions(parent=self)
        )

        self.server_name: StrRef = server_name
        self.database: sql.Database = self._database()
        self.diagnostic_settings: monitor.DiagnosticSetting | None = self._diagnostic_settings()

        self._outputs()

    def _database(self) -> sql.Database:
        max_size_in_bytes: int | None = (
            self.config.max_size_mb * 1024 * 1024 if self.config.max_size_mb else None
        )
        return sql.Database(
            resource_name=self.stack.name_for(
                resource_type=sql.Database, workload_name=self.config.name
            ),
            args=sql.DatabaseArgs(
                resource_group_name=self.stack.resource_group.name,
                server_name=self.server_name,
                elastic_pool_id=self.config.elastic_pool_id,
                database_name=self.stack.name_for(
                    resource_type=sql.Database, workload_name=self.config.name
                ),
                create_mode=self.config.create_mode,
                source_database_id=self.config.source_database_id,
                zone_redundant=self.config.zone_redundant,
                requested_backup_storage_redundancy=self.config.backup_redundancy,
                max_size_bytes=max_size_in_bytes,
                collation=self.config.collation,
                sku=sql.SkuArgs(
                    name=self.config.sku.name,
                    tier=self.config.sku.tier,
                )
                if self.config.sku
                else None,
            ),
            opts=self._opts,
        )

    def _diagnostic_settings(self) -> monitor.DiagnosticSetting | None:
        if self.config.log_workspace_id:
            return diagnostic_setting(
                resource=self.database,
                log_workspace_id=self.config.log_workspace_id,
                metric_categories=[
                    "Basic",
                    "InstanceAndAppAdvanced",
                ],
                log_categories=[
                    "AutomaticTuning",
                    "Blocks",
                    "DatabaseWaitStatistics",
                    "Deadlocks",
                    "Errors",
                    "QueryStoreRuntimeStatistics",
                    "QueryStoreWaitStatistics",
                    "SQLInsights",
                    "SQLSecurityAuditEvents",
                    "Timeouts",
                ],
                opts=pulumi.ResourceOptions(parent=self.database),
            )

    def _outputs(self) -> None:
        self.register_outputs(
            {"database": self.database},
        )

        self.stack.export(
            exports={
                "database": {
                    "id": self.database.id,
                    "name": self.database.name,
                }
            }
        )

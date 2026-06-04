import pulumi

from orbitcloud_graviton.az_lib.types import AzureIdRef
from orbitcloud_graviton.az_mysql import MysqlFlexibleServer, MysqlFlexibleServerConfig
from orbitcloud_graviton.az_postgres import PostgresFlexibleServer, PostgresFlexibleServerConfig
from orbitcloud_graviton.az_sql import (
    SqlDatabase,
    SqlDatabaseConfig,
    SqlServer,
    SqlServerConfig,
)
from orbitcloud_graviton.az_storage import StorageAccount, StorageAccountConfig
from orbitcloud_graviton.pulumi_lib import (
    AzureStack,
    PulumiConfig,
    generate_stack_schema,
    get_azure_stack,
)
from orbitcloud_graviton.pulumi_lib.azure_base import EntraStack, get_entra_stack


class DataZoneBaseConfig(PulumiConfig):
    log_workspace_id: AzureIdRef | None = None

    postgres: PostgresFlexibleServerConfig | None = None
    mysql: MysqlFlexibleServerConfig | None = None
    sql_server: SqlServerConfig | None = None
    sql_databases: list[SqlDatabaseConfig] | None = None
    storage_accounts: list[StorageAccountConfig] | None = None


def deploy() -> None:
    generate_stack_schema(model=DataZoneBaseConfig, output_file=".stack_schema.json")
    config: DataZoneBaseConfig = DataZoneBaseConfig.model_validate({})

    stack: AzureStack = get_azure_stack()
    entra_config: EntraStack = get_entra_stack()

    opts = pulumi.ResourceOptions(parent=stack.resource_group)

    ##########################################
    # PostgreSQL Flexible Server
    ##########################################
    if config.postgres:
        psql_config = (
            config.postgres.model_copy(update={"log_workspace_id": config.log_workspace_id})
            if config.log_workspace_id
            else config.postgres
        )
        PostgresFlexibleServer(
            stack=stack,
            entra_config=entra_config,
            config=psql_config,
            opts=opts,
        )

    ##########################################
    # MySQL Flexible Server
    ##########################################
    if config.mysql:
        mysql_config = (
            config.mysql.model_copy(update={"log_workspace_id": config.log_workspace_id})
            if config.log_workspace_id
            else config.mysql
        )
        MysqlFlexibleServer(
            stack=stack,
            entra_config=entra_config,
            config=mysql_config,
            opts=opts,
        )

    ##########################################
    # Azure SQL Server + Databases
    ##########################################
    if config.sql_server:
        sql_config = (
            config.sql_server.model_copy(update={"log_workspace_id": config.log_workspace_id})
            if config.log_workspace_id
            else config.sql_server
        )
        sql_server = SqlServer(stack=stack, config=sql_config, opts=opts)

        for database in config.sql_databases or []:
            update_kwargs: dict = {}
            if sql_server.elastic_pool:
                update_kwargs["elastic_pool_id"] = sql_server.elastic_pool.id
            if config.log_workspace_id:
                update_kwargs["log_workspace_id"] = config.log_workspace_id

            SqlDatabase(
                stack=stack,
                config=database.model_copy(update=update_kwargs) if update_kwargs else database,
                server_name=sql_server.server.name,
                opts=opts,
            )

    ##########################################
    # Storage Accounts
    ##########################################
    for st in config.storage_accounts or []:
        st_config = (
            st.model_copy(update={"log_workspace_id": config.log_workspace_id})
            if config.log_workspace_id
            else st
        )
        StorageAccount(stack=stack, config=st_config, opts=opts)

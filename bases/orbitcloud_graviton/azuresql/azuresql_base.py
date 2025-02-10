import pulumi
from pulumi_azure_native.resources import ResourceGroup

from orbitcloud_graviton.az_lib.types import AzureIdRef
from orbitcloud_graviton.az_sql import SqlDatabase, SqlDatabaseConfig, SqlServer
from orbitcloud_graviton.az_sql.server import SqlServerConfig
from orbitcloud_graviton.pulumi_lib import (
    AzureStack,
    PulumiConfig,
    generate_stack_schema,
    get_azure_stack,
)


class AzureSqlBaseConfig(PulumiConfig):
    server: SqlServerConfig
    databases: list[SqlDatabaseConfig] | None = None
    log_workspace_id: AzureIdRef | None = None


def deploy() -> None:
    generate_stack_schema(model=AzureSqlBaseConfig, output_file=".stack_schema.json")
    config: AzureSqlBaseConfig = AzureSqlBaseConfig.model_validate({})
    stack: AzureStack = get_azure_stack()

    rg: ResourceGroup = stack.resource_group
    opts = pulumi.ResourceOptions(parent=rg)

    server = SqlServer(
        stack=stack,
        config=config.server.model_copy(update={"log_workspace_id": config.log_workspace_id}),
        opts=opts,
    )

    for database in config.databases or []:
        update_kwargs: dict = {}
        if server.elastic_pool:
            update_kwargs["elastic_pool_id"] = server.elastic_pool.id
        if config.log_workspace_id:
            update_kwargs["log_workspace_id"] = config.log_workspace_id

        SqlDatabase(
            stack=stack,
            config=database.model_copy(update=update_kwargs),
            server_name=server.server.name,
            opts=opts,
        )

import pulumi
from pulumi_azure_native import operationalinsights, resources

from orbitcloud_graviton.az_lib.types import AzureIdRef
from orbitcloud_graviton.az_monitor import LogWorkspaceConfig, log_workspace
from orbitcloud_graviton.az_network import Firewall, FirewallConfig
from orbitcloud_graviton.pulumi_lib import AzureStack, PulumiConfig, get_azure_stack
from orbitcloud_graviton.pulumi_lib.stack_schema import generate_stack_schema


class FirewallBaseConfig(PulumiConfig):
    firewall: FirewallConfig
    log: bool | AzureIdRef | None = True


def deploy_firewall():
    generate_stack_schema(model=FirewallBaseConfig, output_file=".stack_schema.json")
    stack: AzureStack = get_azure_stack()
    config: FirewallBaseConfig = FirewallBaseConfig.model_validate({})

    rg: resources.ResourceGroup = stack.resource_group

    ##########################################
    # Log Workspace
    ##########################################
    if config.log:
        if config.log is True:
            logs: operationalinsights.Workspace = log_workspace(
                config=LogWorkspaceConfig(),
                stack=stack,
                opts=pulumi.ResourceOptions(parent=rg),
            )
            log_workspace_id = logs.id
        elif config.log is not False:
            log_workspace_id = config.log

    ##########################################
    # Firewall
    ##########################################
    Firewall(
        stack=stack,
        config=config.firewall.model_copy(
            update={"log_workspace_id": log_workspace_id if config.log else None}
        ),
        opts=pulumi.ResourceOptions(parent=rg),
    )

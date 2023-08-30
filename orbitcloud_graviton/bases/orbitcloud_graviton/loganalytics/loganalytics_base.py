import pulumi
from pulumi_azure_native import operationalinsights, resources

from orbitcloud_graviton.az_monitor import az_logworkspace
from orbitcloud_graviton.az_resources import az_resource_group

# Move this to a reusable config module
config = pulumi.Config()

base_args = {
    "workload_name": config.get("workload_name") or pulumi.get_project(),
    "location": pulumi.Config("azure-native").get("location"),
    "env": config.require("env"),
}

rg_log: resources.ResourceGroup = az_resource_group(**base_args)

log_workspace: operationalinsights.Workspace = az_logworkspace(
    resource_group=rg_log,
    **base_args,
)

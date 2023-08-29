import pulumi

from pulumi_azure_native import resources, operationalinsights

from orbitcloud_graviton.azure_monitor import (
    loganalytics_workspace,
)
from orbitcloud_graviton.azure_resource_group.core import resource_group

# Move this to a reusable config module
config = pulumi.Config()

base_args = {
    "workload_name": config.get("workload_name") or pulumi.get_project(),
    "location": pulumi.Config("azure-native").get("location"),
    "env": config.require("env"),
}

rg_log: resources.ResourceGroup = resource_group(**base_args)

log_workspace: operationalinsights.Workspace = loganalytics_workspace(
    resource_group=rg_log,
    **base_args,
)

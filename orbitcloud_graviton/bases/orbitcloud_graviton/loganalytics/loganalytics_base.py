import pulumi
from pulumi_azure_native import operationalinsights, resources

from orbitcloud_graviton.az_monitor import az_logworkspace
from orbitcloud_graviton.az_resources import az_resource_group

# Move this to a reusable config module
config = pulumi.Config()

workload_name: str = config.get("workload_name") or pulumi.get_project()
env: str = config.require("env")
location: str = pulumi.Config("azure-native").require("location")

rg_log: resources.ResourceGroup = az_resource_group(
    workload_name=workload_name,
    location=location,
    env=env,
)

log_workspace: operationalinsights.Workspace = az_logworkspace(
    resource_group=rg_log,
    workload_name=config.get("workload_name") or pulumi.get_project(),
    env=env,
    location=location,
)

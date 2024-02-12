""" Core module for creating Azure LogAnalytics Workspaces """
from typing import Dict, Optional

import pulumi
from pulumi_azure_native import operationalinsights, resources

from orbitcloud_graviton.az_lib import resource_namer


def log_workspace(
    resource_group: resources.ResourceGroup,
    workload_name: str,
    env: str,
    location: str,
    sku_name="PerGB2018",
    tags: Optional[Dict[str, str]] = None,
    opts: Optional[pulumi.ResourceOptions] = None,
) -> operationalinsights.Workspace:
    workspace_name = resource_namer(
        operationalinsights.Workspace, workload_name, env, location=location
    )

    return operationalinsights.Workspace(
        workspace_name,
        resource_group_name=resource_group.name,
        location=location,
        sku=operationalinsights.WorkspaceSkuArgs(
            name=sku_name,
        ),
        tags=tags,
        opts=opts,
    )

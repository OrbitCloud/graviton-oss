""" Core module for creating Azure LogAnalytics Workspaces """
from typing import Mapping, Optional

import pulumi

from pulumi_azure_native import resources, operationalinsights

from orbitcloud_graviton.azure_helpers import resource_namer


def loganalytics_workspace(
    resource_group: resources.ResourceGroup,
    workload_name: str,
    env: str,
    location: str,
    sku_name="PerGB2018",
    tags: Optional[Mapping[str, str]] = None,
    opts: Optional[pulumi.ResourceOptions] = None,
) -> operationalinsights.Workspace:
    """
    Create an Azure LogAnalytics Workspace

    Args:
        resource_group (resources.ResourceGroup): The resource group to create the workspace in
        workload_name (str): The name of the workload
        sku_name (str, optional): The sku name to use. Defaults to "PerGB2018".
        tags (Optional[Mapping[str, str]], optional):
            Tags to add to the workspace. Defaults to None.
        opts (Optional[pulumi.ResourceOptions], optional):
            Options to pass to the workspace. Defaults to None.

    Returns:
        operationalinsights.Workspace: The created workspace
    """
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

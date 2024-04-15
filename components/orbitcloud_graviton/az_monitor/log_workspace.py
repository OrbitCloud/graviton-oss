"""Core module for creating Azure LogAnalytics Workspaces"""

from typing import Literal, Optional

import pulumi
from pulumi_azure_native import operationalinsights
from pydantic import BaseModel, ConfigDict, Field

from orbitcloud_graviton.pulumi_lib import AzureStack


class LogWorkspaceConfig(BaseModel):
    public_network_access_for_ingestion: Optional[operationalinsights.PublicNetworkAccessType] = (
        operationalinsights.PublicNetworkAccessType.ENABLED
    )
    public_network_access_for_query: Optional[operationalinsights.PublicNetworkAccessType] = (
        operationalinsights.PublicNetworkAccessType.ENABLED
    )

    retention_in_days: Optional[Literal[30, 31, 60, 90, 120, 180, 270, 365, 550, 730]] = 30
    sku: operationalinsights.WorkspaceSkuNameEnum = Field(
        default=operationalinsights.WorkspaceSkuNameEnum.PER_GB2018, validate_default=True
    )
    daily_quota_gb: Optional[float] = None
    disable_local_auth: Optional[bool] = False

    model_config = ConfigDict(use_enum_values=True)


def log_workspace(
    config: LogWorkspaceConfig,
    stack: AzureStack,
    opts: Optional[pulumi.ResourceOptions] = None,
) -> operationalinsights.Workspace:
    pulumi.debug(config.sku)
    return operationalinsights.Workspace(
        resource_name=stack.name_for(operationalinsights.Workspace),
        resource_group_name=stack.resource_group.name,
        location=stack.location,
        public_network_access_for_ingestion=config.public_network_access_for_ingestion,
        public_network_access_for_query=config.public_network_access_for_query,
        retention_in_days=config.retention_in_days,
        features=operationalinsights.WorkspaceFeaturesArgs(
            disable_local_auth=config.disable_local_auth,
        ),
        workspace_capping=operationalinsights.WorkspaceCappingArgs(
            daily_quota_gb=config.daily_quota_gb,
        )
        if config.daily_quota_gb
        else None,
        sku=operationalinsights.WorkspaceSkuArgs(
            name=config.sku,
        ),
        opts=opts,
    )

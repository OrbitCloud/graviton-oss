"""Azure Application Insights Module"""
from typing import Optional

import pulumi
from pulumi_azure_native import insights
from pydantic import BaseModel, ConfigDict

from orbitcloud_graviton.az_lib.types import AzureIdRef
from orbitcloud_graviton.pulumi_lib.azure_base import AzureBase


class AppInsightsConfig(BaseModel):
    retention_in_days: int = 30
    log_workspace_id: AzureIdRef

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


def app_insights(
    stack: AzureBase,
    config: AppInsightsConfig,
    opts: Optional[pulumi.ResourceOptions] = None,
) -> insights.Component:
    """
    Create an Application Insights component
    """

    appi = insights.Component(
        resource_name=stack.name_for(insights.Component),
        location=stack.location,
        resource_group_name=stack.resource_group.name,
        kind="web",
        application_type=insights.ApplicationType.WEB,
        retention_in_days=config.retention_in_days,
        workspace_resource_id=config.log_workspace_id,
        opts=opts,
    )

    return appi

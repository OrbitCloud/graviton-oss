from typing import List, Optional, Union

import pulumi
from pulumi_azure_native import insights


def diagnostic_setting(
    resource: pulumi.CustomResource,
    log_workspace_id: Union[str, pulumi.Output[str]],
    log_categories: Optional[List[str]] = None,
    metric_categories: Optional[List[str]] = None,
    opts=None,
) -> insights.DiagnosticSetting:
    metric_categories = metric_categories or ["AllMetrics"]
    diag_name: str = "diag-" + resource._name

    settings = insights.DiagnosticSetting(
        resource_name=diag_name,
        resource_uri=resource.id,
        workspace_id=log_workspace_id,
        metrics=[
            insights.MetricSettingsArgs(
                category=category,
                enabled=True,
            )
            for category in metric_categories
        ]
        if metric_categories
        else None,
        logs=[
            insights.LogSettingsArgs(
                category=category,
                enabled=True,
            )
            for category in log_categories
        ]
        if log_categories
        else None,
        opts=opts,
    )
    return settings

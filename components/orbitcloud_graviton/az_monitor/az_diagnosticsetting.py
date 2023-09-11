from typing import Any, List, Optional
import pulumi
from pulumi_azure_native import insights, operationalinsights, resources
from orbitcloud_graviton.az_lib import resource_namer


def az_diagnosticsetting(
    resource: Any,
    log_workspace: operationalinsights.Workspace,
    log_categories: List[str] = [],
    metric_categories: List[str] = ["AllMetrics"],
    opts=None,
) -> insights.DiagnosticSetting:
    if not hasattr(resource, "id"):
        raise ValueError("target resource must have an id attribute")

    if not hasattr(resource, "name"):
        raise ValueError("target resource must have a name attribute")

    diag_name: str = "diag-" + resource._name

    settings = insights.DiagnosticSetting(
        resource_name=diag_name,
        resource_uri=resource.id,
        workspace_id=log_workspace.id,
        metrics=[
            insights.MetricSettingsArgs(
                category=category,
                enabled=True,
            )
            for category in metric_categories
        ],
        logs=[
            insights.LogSettingsArgs(
                category=category,
                enabled=True,
            )
            for category in log_categories
        ],
        opts=opts,
    )
    return settings

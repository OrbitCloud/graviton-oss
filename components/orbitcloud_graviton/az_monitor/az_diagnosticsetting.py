from typing import Any, List, Optional

from pulumi_azure_native import insights, operationalinsights


def az_diagnosticsetting(
    resource: Any,
    log_workspace: operationalinsights.Workspace,
    log_categories: Optional[List[str]] = None,
    metric_categories: Optional[List[str]] = None,
    opts=None,
) -> insights.DiagnosticSetting:
    if not hasattr(resource, "id"):
        raise ValueError("target resource must have an id attribute")

    if not hasattr(resource, "name"):
        raise ValueError("target resource must have a name attribute")

    metric_categories = metric_categories or ["AllMetrics"]

    # pylint: disable=protected-access
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

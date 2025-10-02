import pulumi
from pulumi_azure_native import monitor


def diagnostic_setting(
    resource: pulumi.CustomResource,
    log_workspace_id: str | pulumi.Output[str],
    log_categories: list[str] | None = None,
    metric_categories: list[str] | None = None,
    opts=None,
) -> monitor.DiagnosticSetting:
    # Have a look at the supported logs and metrics here:
    # https://learn.microsoft.com/en-us/azure/azure-monitor/reference/supported-logs/logs-index

    metric_categories = metric_categories or ["AllMetrics"]
    diag_name: str = "diag-" + resource._name

    settings = monitor.DiagnosticSetting(
        resource_name=diag_name,
        resource_uri=resource.id,
        workspace_id=log_workspace_id,
        metrics=[
            monitor.MetricSettingsArgs(
                category=category,
                enabled=True,
            )
            for category in metric_categories
        ]
        if metric_categories
        else None,
        logs=[
            monitor.LogSettingsArgs(
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

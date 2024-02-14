from .az_diagnosticsetting import diagnostic_setting
from .insights import AppInsightsConfig, app_insights
from .log_workspace import LogWorkspaceConfig, log_workspace

__all__ = [
    "log_workspace",
    "diagnostic_setting",
    "LogWorkspaceConfig",
    "app_insights",
    "AppInsightsConfig",
]

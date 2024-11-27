import pulumi
from pulumi_azure_native import appconfiguration as pam_appconfig
from pulumi_azure_native import insights
from pydantic import BaseModel, ConfigDict, Field

from orbitcloud_graviton.az_lib.types import AzureIdRef, StrRef
from orbitcloud_graviton.az_monitor import diagnostic_setting
from orbitcloud_graviton.pulumi_lib import AzureStack


class AppConfigurationConfig(BaseModel):
    public_network_access: pam_appconfig.PublicNetworkAccess = (
        pam_appconfig.PublicNetworkAccess.DISABLED
    )

    keys: dict[str, StrRef | str] | None = None
    label: str | None = None

    export_endpoint_as_secret: str | None = Field(default=None, pattern="^[a-z0-9_-]+$")

    log_workspace_id: AzureIdRef | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class AppConfiguration(pulumi.ComponentResource):
    def __init__(
        self,
        stack: AzureStack,
        config: AppConfigurationConfig,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        self.stack: AzureStack = stack
        self.config: AppConfigurationConfig = config

        super().__init__(
            "Graviton:AppConfiguration",
            name=f"appcs-{stack.workload_name}-{stack.env}",
            props=None,
            opts=opts,
        )

        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts1=opts, opts2=pulumi.ResourceOptions(parent=self)
        )

        self.app_config: pam_appconfig.ConfigurationStore = self._app_config()
        self._config_keys()

        self._outputs()

    def _app_config(self) -> pam_appconfig.ConfigurationStore:
        return pam_appconfig.ConfigurationStore(
            resource_name=self.stack.name_for(resource_type=pam_appconfig.ConfigurationStore),
            args=pam_appconfig.ConfigurationStoreArgs(
                location=self.stack.location,
                resource_group_name=self.stack.resource_group.name,
                sku=pam_appconfig.SkuArgs(
                    name="Standard",
                ),
            ),
            opts=self._opts,
        )

    def _config_keys(self) -> None:
        if self.config.keys:
            for key, value in self.config.keys.items():
                pam_appconfig.KeyValue(
                    resource_name=self.stack.name_for(
                        resource_type=pam_appconfig.KeyValue,
                        workload_name=(self.stack.workload_name + key),
                    ),
                    args=pam_appconfig.KeyValueArgs(
                        config_store_name=self.app_config.name,
                        resource_group_name=self.stack.resource_group.name,
                        key_value_name=f"{key}${self.config.label}" if self.config.label else key,
                        value=value,
                    ),
                    opts=pulumi.ResourceOptions.merge(
                        self._opts, pulumi.ResourceOptions(parent=self.app_config)
                    ),
                )

    def _diagnostic_settings(self) -> insights.DiagnosticSetting | None:
        if self.config.log_workspace_id:
            return diagnostic_setting(
                resource=self.app_config,
                log_workspace_id=self.config.log_workspace_id,
                metric_categories=["AllMetrics"],
                log_categories=[
                    "SomeCategory",
                ],
                opts=pulumi.ResourceOptions(parent=self.app_config),
            )

    def _outputs(self) -> None:
        self.register_outputs(
            {"app_config": self.app_config},
        )

        self.stack.export(
            exports={
                "app_config": {
                    "id": self.app_config.id,
                    "name": self.app_config.name,
                }
            }
        )

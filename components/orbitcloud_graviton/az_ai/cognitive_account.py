from ipaddress import IPv4Address
from typing import Literal

import pulumi

# from pulumi_azure_native import
from pulumi_azure_native import cognitiveservices as ai
from pulumi_azure_native import monitor
from pydantic import BaseModel, ConfigDict

from orbitcloud_graviton.az_lib import location_abbr
from orbitcloud_graviton.az_lib.types import AzureIdRef, StrRef
from orbitcloud_graviton.az_monitor import diagnostic_setting
from orbitcloud_graviton.az_network import PrivateEndpoint, PrivateEndpointConfig
from orbitcloud_graviton.pulumi_lib import AzureStack, EntraStack

# Resource name prefix per `kind`. The metadata YAML carries `oai` for the
# CognitiveServices Account resource type, which is OpenAI-flavoured; for
# AIServices (Azure AI Foundry) we want `aif` instead.
_PREFIX_BY_KIND: dict[str, str] = {
    "OpenAI": "oai",
    "AIServices": "aif",
}


class CognitiveAccountConfig(BaseModel):
    kind: Literal["OpenAI", "AIServices"] = "AIServices"
    name: str | None = None
    allowed_public_ips: list[IPv4Address | StrRef] | None = None
    custom_domain_prefix: str | None = None
    private_endpoints: list[PrivateEndpointConfig] | None = None

    log_workspace_id: AzureIdRef | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class CognitiveAccount(pulumi.ComponentResource):
    def __init__(
        self,
        stack: AzureStack,
        entra_config: EntraStack,
        config: CognitiveAccountConfig,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        self.stack: AzureStack = stack
        self.config: CognitiveAccountConfig = config
        self.entra_config: EntraStack = entra_config

        super().__init__(
            "Graviton:CognitiveAccount",
            name=f"cognitiveaccount-{stack.workload_name}-{stack.env}",
            props=None,
            opts=opts,
        )

        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts1=opts, opts2=pulumi.ResourceOptions(parent=self)
        )

        self.account: ai.Account = self._account()
        self.private_endpoints: list[PrivateEndpoint] | None = self._private_endpoints()
        self.diagnostic_settings: monitor.DiagnosticSetting | None = self._diagnostic_settings()

        self._outputs()

    def _account_name(self) -> str:
        if self.config.name:
            return self.config.name
        prefix = _PREFIX_BY_KIND[self.config.kind]
        return (
            f"{prefix}-{self.stack.workload_name}-{self.stack.env}-"
            f"{location_abbr(location=self.stack.location)}-01"
        )

    def _account(self) -> ai.Account:
        name: str = self._account_name()
        return ai.Account(
            resource_name=name,
            args=ai.AccountArgs(
                account_name=name,
                resource_group_name=self.stack.resource_group.name,
                location=self.stack.location,
                kind=self.config.kind,
                sku=ai.SkuArgs(name="S0"),
                identity=ai.IdentityArgs(
                    type=ai.ResourceIdentityType.SYSTEM_ASSIGNED,
                ),
                properties=ai.AccountPropertiesArgs(
                    public_network_access=ai.PublicNetworkAccess.ENABLED
                    if self.config.allowed_public_ips
                    else ai.PublicNetworkAccess.DISABLED,
                    network_acls=ai.NetworkRuleSetArgs(
                        default_action=ai.NetworkRuleAction.DENY,
                        ip_rules=[
                            ai.IpRuleArgs(value=str(ip)) for ip in self.config.allowed_public_ips
                        ]
                        if self.config.allowed_public_ips
                        else None,
                    ),
                    custom_sub_domain_name=self.config.custom_domain_prefix,
                ),
            ),
            opts=self._opts,
        )

    def _private_endpoints(self) -> list[PrivateEndpoint] | None:
        if self.config.private_endpoints:
            return [
                PrivateEndpoint(
                    stack=self.stack,
                    config=endpoint,
                    target_resource=self.account,
                    opts=pulumi.ResourceOptions(parent=self.account),
                )
                for endpoint in self.config.private_endpoints
            ]

    def _diagnostic_settings(self) -> monitor.DiagnosticSetting | None:
        if self.config.log_workspace_id:
            return diagnostic_setting(
                resource=self.account,
                log_workspace_id=self.config.log_workspace_id,
                metric_categories=["AllMetrics"],
                log_categories=[
                    "Audit",
                    "AzureOpenAIRequestUsage",
                    "RequestResponse",
                    "Trace",
                ],
                opts=pulumi.ResourceOptions(parent=self.account),
            )

    def _outputs(self) -> None:
        self.register_outputs(
            {
                "cognitiveaccount": self.account,
                "private_endpoints": self.private_endpoints,
            }
        )

        self.stack.export(
            exports={
                "cognitiveaccount": {
                    "id": self.account.id,
                    "name": self.account.name,
                }
            }
        )

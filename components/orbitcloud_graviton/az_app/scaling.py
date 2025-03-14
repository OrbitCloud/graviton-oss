from typing import Annotated

from pulumi_azure_native.app import v20241002preview as app
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .scalers.app_rules import AzureQueueScaleRule, HttpScaleRule, TcpScaleRule
from .scalers.custom import CustomScaleRule

## Custom scalers
# isort: off
from .scalers.azure_blob import AzureBlobRule
from .scalers.azure_queue import AzureQueueRule

# Add custom rule types to the list of rule types
CustomRuleTypes = Annotated[AzureBlobRule | AzureQueueRule, Field(discriminator="rule_type")]

AppRuleTypes = (
    Annotated[
        HttpScaleRule | TcpScaleRule,
        Field(discriminator="rule_type"),
    ]
    | CustomRuleTypes
    | CustomScaleRule
)


class ContainerAppScaleConfig(BaseModel):
    max_replicas: int | None = 10
    min_replicas: int | None = 1
    rules: dict[str, AppRuleTypes] | None = None

    def args(self) -> app.ScaleArgs:
        rules = []
        if self.rules:
            for name, rule in self.rules.items() or []:
                if isinstance(rule, HttpScaleRule):
                    rules.append(app.ScaleRuleArgs(name=name, http=rule.args()))
                elif isinstance(rule, TcpScaleRule):
                    rules.append(app.ScaleRuleArgs(name=name, tcp=rule.args()))
                elif isinstance(rule, AzureQueueScaleRule):
                    rules.append(app.ScaleRuleArgs(name=name, azure_queue=rule.args()))
                else:
                    rules.append(app.ScaleRuleArgs(name=name, custom=rule.args()))

        return app.ScaleArgs(
            min_replicas=self.min_replicas,
            max_replicas=self.max_replicas,
            rules=rules if rules else None,
        )

    @model_validator(mode="after")
    def min_replicas_or_max_replicas(m: "ContainerAppScaleConfig") -> "ContainerAppScaleConfig":
        if not m.min_replicas and not m.max_replicas:
            raise ValueError("Either min_replicas or max_replicas must be set.")
        return m

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

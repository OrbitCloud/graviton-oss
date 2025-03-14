from pulumi_azure_native.app import v20241002preview as app
from pydantic import BaseModel, ConfigDict

from .auth import ScaleRuleAuth


class CustomScaleRule(BaseModel):
    rule_type: str
    auth: list[ScaleRuleAuth] | None = None
    metadata: dict | BaseModel

    def args(self) -> app.CustomScaleRuleArgs:
        return app.CustomScaleRuleArgs(
            type=self.rule_type,
            auth=[
                app.ScaleRuleAuthArgs(
                    secret_ref=auth.secret_ref,
                    trigger_parameter=auth.trigger_parameter,
                )
                for auth in self.auth or []
            ],
            metadata=self.metadata.model_dump(by_alias=True, exclude_none=True)
            if isinstance(self.metadata, BaseModel)
            else self.metadata,
        )

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

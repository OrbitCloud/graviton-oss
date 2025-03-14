from typing import Literal

from pulumi_azure_native.app import v20241002preview as app
from pydantic import BaseModel, ConfigDict, Field

from .auth import ScaleRuleAuth


class HttpScaleRule(BaseModel):
    rule_type: Literal["http"] = "http"
    concurrent_requests: int = 10
    auth: list[ScaleRuleAuth] | None = None

    def args(self) -> app.HttpScaleRuleArgs:
        return app.HttpScaleRuleArgs(
            auth=[
                app.ScaleRuleAuthArgs(
                    secret_ref=auth.secret_ref,
                    trigger_parameter=auth.trigger_parameter,
                )
                for auth in self.auth or []
            ],
            metadata={
                "concurrentRequests": str(self.concurrent_requests),
            },
        )

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class TcpScaleRule(BaseModel):
    rule_type: Literal["tcp"] = "tcp"
    concurrent_connections: int = 10
    auth: list[ScaleRuleAuth] | None = None

    def args(self) -> app.TcpScaleRuleArgs:
        return app.TcpScaleRuleArgs(
            auth=[
                app.ScaleRuleAuthArgs(
                    secret_ref=auth.secret_ref,
                    trigger_parameter=auth.trigger_parameter,
                )
                for auth in self.auth or []
            ],
            metadata={
                "concurrentConnections": str(self.concurrent_connections),
            },
        )

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class AzureQueueScaleRule(BaseModel):
    rule_type: Literal["azure-queue"] = "azure-queue"
    queue_name: str
    message_count: int = Field(
        ..., description="The number of messages in the queue to trigger scaling."
    )
    auth: list[ScaleRuleAuth] | None = None

    def args(self) -> app.QueueScaleRuleArgs:
        return app.QueueScaleRuleArgs(
            # Waiting for v20240802preview to become available
            # identity="system",
            auth=[
                app.ScaleRuleAuthArgs(
                    secret_ref=auth.secret_ref,
                    trigger_parameter=auth.trigger_parameter,
                )
                for auth in self.auth or []
            ],
            queue_name=self.queue_name,
            queue_length=self.message_count,
        )

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

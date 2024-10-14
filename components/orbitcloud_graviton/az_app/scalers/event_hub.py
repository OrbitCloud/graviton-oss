from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from .custom import CustomScaleRule

# Keda docs
# https://keda.sh/docs/latest/scalers/azure-storage-queue/3


class EventHubRuleMetadata(BaseModel):
    eventhubNamespace: str
    eventhubName: str
    storageAccountName: str
    blobContainer: str | None = None
    consumerGroup: str = "$Default"
    checkpointStrategy: Literal["azureFunction", "blobMetadata", "goSdk", "dapr"] | None = None
    unprocessedEventThreshold: Decimal | None = None
    activationUnprocessedEventThreshold: Decimal | None = None

    @model_validator(mode="after")
    def validate_blob_container(
        m: "EventHubRuleMetadata",
    ) -> "EventHubRuleMetadata":
        if (
            m.checkpointStrategy == "blobMetadata" or not m.checkpointStrategy
        ) and not m.blobContainer:
            raise ValueError(
                "blobContainer is required when checkpointStrategy is blobMetadata or not set."
            )
        return m

    model_config = ConfigDict(
        extra="allow",
        coerce_numbers_to_str=True,
    )


class EventHubRule(CustomScaleRule):
    rule_type: Literal["azure-event-hub"]
    metadata: EventHubRuleMetadata

    model_config = ConfigDict(
        extra="forbid",
        coerce_numbers_to_str=True,
    )

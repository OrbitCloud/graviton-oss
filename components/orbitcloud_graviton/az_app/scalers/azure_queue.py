from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

from .custom import CustomScaleRule

# Keda docs
# https://keda.sh/docs/latest/scalers/azure-storage-queue/3


class AzureQueueRuleMetadata(BaseModel):
    accountName: str
    queueName: str

    # Optional configurations
    queueLength: Decimal | None = None
    activationQueueLength: Decimal | None = None
    queueLengthStrategy: Literal["all", "visibleonly"] | None = None

    model_config = ConfigDict(
        extra="allow",
        coerce_numbers_to_str=True,
    )


class AzureQueueRule(CustomScaleRule):
    rule_type: Literal["azure-queue"]
    metadata: AzureQueueRuleMetadata

    model_config = ConfigDict(
        extra="forbid",
        coerce_numbers_to_str=True,
    )

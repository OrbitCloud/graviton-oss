from typing import Literal

from pydantic import BaseModel, ConfigDict

from .custom import CustomScaleRule

# Keda docs
# https://keda.sh/docs/latest/scalers/azure-storage-blob/


class AzureBlobRuleMetadata(BaseModel):
    accountName: str
    blobContainerName: str

    # Optional configurations
    activationBlobCount: int | None = None
    blobCount: str | None = None
    blobPrefix: str | None = None
    blobDelimiter: str | None = None
    recursive: Literal["true", "false"] | None = None
    globPattern: str | None = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True, extra="allow", coerce_numbers_to_str=True
    )


class AzureBlobRule(CustomScaleRule):
    rule_type: Literal["azure-blob"]
    metadata: AzureBlobRuleMetadata

    model_config = ConfigDict(
        arbitrary_types_allowed=True, extra="forbid", coerce_numbers_to_str=True
    )

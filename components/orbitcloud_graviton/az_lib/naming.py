from typing import Optional

from pydantic import BaseModel, ConfigDict


class ResourceNameRule(BaseModel):
    prefix: str
    alphanumeric: Optional[bool] = False
    lowercase: Optional[bool] = False
    max_length: Optional[int] = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

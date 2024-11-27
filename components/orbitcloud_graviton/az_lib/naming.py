from pydantic import BaseModel, ConfigDict


class ResourceNameRule(BaseModel):
    prefix: str
    alphanumeric: bool | None = False
    lowercase: bool | None = False
    max_length: int | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

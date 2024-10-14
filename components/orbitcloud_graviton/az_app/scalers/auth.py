from pydantic import BaseModel, ConfigDict


class ScaleRuleAuth(BaseModel):
    secret_ref: str
    trigger_parameter: str

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

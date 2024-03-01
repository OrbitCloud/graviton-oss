from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from orbitcloud_graviton.pulumi_lib.types import DomainName


class ConsumptionProfile(BaseModel):
    workload_type: Literal["Consumption"] = "Consumption"
    name: Literal["Consumption"] = "Consumption"

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class DedicatedProfile(BaseModel):
    name: str = Field(..., title="Profile Name", description="Name of the dedicated profile")
    workload_type: Literal["D4", "D8", "E4", "E8"] = Field(
        ...,
        title="Instance size",
        description="Size of the instance",
        examples=["D4", "D8", "E4", "E8"],
    )
    minimum_count: Annotated[int, Field(ge=0)] = Field(
        ..., title="Minimum number of instances to run"
    )
    maximum_count: Annotated[int, Field(gt=0)] = Field(
        ..., title="Maximum number of instances to run"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class CustomDomain(BaseModel):
    dns_suffix: DomainName
    cert_password: SecretStr
    cert_contents: SecretStr

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

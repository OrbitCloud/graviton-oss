from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ContainerProbeConfig(BaseModel):
    probe_type: Literal["Liveness", "Readiness", "Startup"] = Field(
        default="Liveness", description="The type of probe."
    )
    initial_delay_seconds: int | None = Field(
        default=1,
        ge=1,
        le=60,
        description="Number of seconds after the container has started before liveness probes are initiated. Minimum value is 1. Maximum value is 60.",
    )
    interval_seconds: int | None = Field(
        default=10,
        ge=1,
        le=240,
        description="How often (in seconds) to perform the probe. Default to 10 seconds. Minimum value is 1. Maximum value is 240.",
    )
    success_threshold: int | None = Field(
        default=1,
        gt=0,
        le=10,
        description="Minimum consecutive successes for the probe to be considered successful after having failed. Defaults to 1. Must be 1 for liveness and startup. Minimum value is 1. Maximum value is 10.",
    )
    failure_threshold: int | None = Field(
        default=3,
        gt=1,
        le=10,
        description="Minimum consecutive failures for the probe to be considered failed after having succeeded. Defaults to 3. Minimum value is 1. Maximum value is 10.",
    )
    timeout_seconds: int | None = Field(
        default=1,
        ge=1,
        le=240,
        description="Number of seconds after which the probe times out. Defaults to 1 second. Minimum value is 1. Maximum value is 240.",
    )

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

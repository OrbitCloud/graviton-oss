from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ContainerProbeConfig(BaseModel):
    probe_type: Literal["Liveness", "Readiness", "Startup"] = Field(
        default="Liveness", description="The type of probe."
    )
    initial_delay_seconds: Optional[int] = Field(
        default=1,
        ge=1,
        le=60,
        description="Number of seconds after the container has started before liveness probes are initiated. Minimum value is 1. Maximum value is 60.",
    )
    interval_seconds: Optional[int] = Field(
        default=10,
        ge=1,
        le=240,
        description="How often (in seconds) to perform the probe. Default to 10 seconds. Minimum value is 1. Maximum value is 240.",
    )
    success_threshold: Optional[int] = Field(
        default=1,
        gt=0,
        le=10,
        description="Minimum consecutive successes for the probe to be considered successful after having failed. Defaults to 1. Must be 1 for liveness and startup. Minimum value is 1. Maximum value is 10.",
    )
    failure_threshold: Optional[int] = Field(
        default=3,
        gt=1,
        le=10,
        description="Minimum consecutive failures for the probe to be considered failed after having succeeded. Defaults to 3. Minimum value is 1. Maximum value is 10.",
    )
    timeout_seconds: Optional[int] = Field(
        default=1,
        ge=1,
        le=240,
        description="Number of seconds after which the probe times out. Defaults to 1 second. Minimum value is 1. Maximum value is 240.",
    )
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ContainerResourcesConfig(BaseModel):
    cpu: float = Field(
        default=0.25,
        ge=0.1,
        le=4.0,
        description="The CPU request for the container. Default is 0.5. Minimum value is 0.5. Maximum value is 4.0.",
    )
    memory_gb: float = Field(
        default=0.5,
        ge=0.1,
        le=16.0,
        description="The memory request for the container. Default is 0.25Gi. Maximum is 8Gi for consumption and 16Gi for dedicated environments.",
    )

    CONSUMPTION_COMBINATIONS: list[tuple[float, float]] = [
        (0.25, 0.5),
        (0.5, 1.0),
        (0.75, 1.5),
        (1.0, 2.0),
        (1.25, 2.5),
        (1.5, 3.0),
        (1.75, 3.5),
        (2.0, 4.0),
        (2.25, 4.5),
        (2.5, 5.0),
        (2.75, 5.5),
        (3.0, 6.0),
        (3.25, 6.5),
        (3.5, 7),
        (3.75, 7.5),
        (4.0, 8),
    ]

    def validate_consumption_combinations(self) -> None:
        if (self.cpu, self.memory_gb) not in self.CONSUMPTION_COMBINATIONS:
            raise ValueError(
                f"Invalid combination of CPU and memory when using the consumption profile: {self.cpu} CPU and {self.memory_gb} memory. Valid combinations are: {self.CONSUMPTION_COMBINATIONS}"
            )

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ResiliencyCircuitBreaker(BaseModel):
    consecutive_errors: int
    interval_in_seconds: int
    max_ejection_percent: int = Field(default=..., ge=0, le=100)

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ResiliencyHttpConnectionPool(BaseModel):
    http1_max_pending_requests: int
    http2_max_requests: int
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ResiliencyHttpRetry(BaseModel):
    error_types: Literal[
        "5xx", "connect-failure", "reset", "retriable-headers", "retriable-status-codes"
    ]
    max_retries: int
    initial_delay_ms: int
    max_interval_ms: int
    http_status_codes: Optional[list[int]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ResiliencyTcpConnectionPool(BaseModel):
    max_connections: int

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ResiliencyTcpRetries(BaseModel):
    max_retries: int

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ResiliencyTimeout(BaseModel):
    connection_timeout_seconds: int
    response_timeout_seconds: int

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class AppResiliencyConfig(BaseModel):
    timeout: Optional[ResiliencyTimeout] = None
    http_connection_pool: Optional[ResiliencyHttpConnectionPool] = None
    http_retry: Optional[ResiliencyHttpRetry] = None
    circuit_breaker: Optional[ResiliencyCircuitBreaker] = None
    tcp_connection_pool: Optional[ResiliencyTcpConnectionPool] = None
    tcp_retries: Optional[ResiliencyTcpRetries] = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

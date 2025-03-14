from typing import Literal

import pulumi
from pulumi_azure_native.app.v20241002preview import (
    AppResiliency,
    AppResiliencyArgs,
    CircuitBreakerPolicyArgs,
    HeaderMatchArgs,
    HttpConnectionPoolArgs,
    HttpRetryPolicyArgs,
    TcpConnectionPoolArgs,
    TcpRetryPolicyArgs,
    TimeoutPolicyArgs,
)
from pydantic import BaseModel, ConfigDict, Field, model_validator

from orbitcloud_graviton.pulumi_lib.azure_base import AzureStack


class ResiliencyCircuitBreaker(BaseModel):
    consecutive_errors: int = Field(default=..., gt=0)
    interval_in_seconds: int = Field(default=..., gt=0)
    max_ejection_percent: int = Field(default=..., gt=0, le=100)

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ResiliencyHttpConnectionPool(BaseModel):
    http1_max_pending_requests: int
    http2_max_requests: int
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ResiliencyHttpHeaders(BaseModel):
    name: str
    exact_match: str | None = None
    prefix_match: str | None = None
    suffix_match: str | None = None

    @model_validator(mode="after")
    def one_match_method(m: "ResiliencyHttpHeaders") -> "ResiliencyHttpHeaders":
        if (
            sum(
                1
                for field in ["exact_match", "prefix_match", "suffix_match"]
                if getattr(m, field) is not None
            )
            != 1
        ):
            raise ValueError(
                "Exactly one of 'exact_match', 'prefix_match', 'suffix_match' must be set."
            )
        return m

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ResiliencyHttpRetry(BaseModel):
    error_types: list[
        Literal[
            "5xx",
            "connect-failure",
            "reset",
            "retriable-headers",
            "retriable-status-codes",
            "retriable-4xx",
        ]
    ]
    max_retries: int = Field(default=..., gt=0)
    initial_delay_ms: int = Field(default=..., gt=0)
    max_interval_ms: int = Field(default=..., gt=0)
    http_status_codes: list[int] | None = None
    headers: list[ResiliencyHttpHeaders] | None = None

    @model_validator(mode="after")
    def validate_headers(m: "ResiliencyHttpRetry") -> "ResiliencyHttpRetry":
        if ("retriable-headers" in m.error_types and not m.headers) or (
            m.headers and "retriable-headers" not in m.error_types
        ):
            raise ValueError(
                "If 'retriable-headers' is in 'error_types', 'headers' must be set and vice versa."
            )
        return m

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ResiliencyTcpConnectionPool(BaseModel):
    max_connections: int = Field(default=..., gt=0)

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ResiliencyTcpRetries(BaseModel):
    max_retries: int = Field(default=..., gt=0)

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ResiliencyTimeout(BaseModel):
    connection_timeout_seconds: int = Field(default=..., gt=0)
    response_timeout_seconds: int = Field(default=..., gt=0)

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class AppResiliencyConfig(BaseModel):
    timeout: ResiliencyTimeout | None = None
    http_connection_pool: ResiliencyHttpConnectionPool | None = None
    http_retry: ResiliencyHttpRetry | None = None
    circuit_breaker: ResiliencyCircuitBreaker | None = None
    tcp_connection_pool: ResiliencyTcpConnectionPool | None = None
    tcp_retries: ResiliencyTcpRetries | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


def app_resiliency(
    app_name: str,
    stack: AzureStack,
    config: AppResiliencyConfig | None = None,
    opts: pulumi.ResourceOptions | None = None,
) -> AppResiliency | None:
    if not config:
        return None

    # Workaround for name length limit in Azure
    resiliency_name = f"appres-{app_name or stack.workload_name}"[0:32].removesuffix("-")

    return AppResiliency(
        resource_name=resiliency_name,
        args=AppResiliencyArgs(
            name=resiliency_name,
            app_name=app_name,
            resource_group_name=stack.resource_group.name,
            circuit_breaker_policy=CircuitBreakerPolicyArgs(
                consecutive_errors=config.circuit_breaker.consecutive_errors,
                interval_in_seconds=config.circuit_breaker.interval_in_seconds,
                max_ejection_percent=config.circuit_breaker.max_ejection_percent,
            )
            if config.circuit_breaker
            else None,
            http_connection_pool=HttpConnectionPoolArgs(
                http1_max_pending_requests=config.http_connection_pool.http1_max_pending_requests,
                http2_max_requests=config.http_connection_pool.http2_max_requests,
            )
            if config.http_connection_pool
            else None,
            http_retry_policy=HttpRetryPolicyArgs(
                max_retries=config.http_retry.max_retries,
                max_interval_in_milliseconds=config.http_retry.max_interval_ms,
                initial_delay_in_milliseconds=config.http_retry.initial_delay_ms,
                errors=config.http_retry.error_types,
                http_status_codes=config.http_retry.http_status_codes,
                headers=[
                    HeaderMatchArgs(
                        header=header.name,
                        exact_match=header.exact_match,
                        prefix_match=header.prefix_match,
                        suffix_match=header.suffix_match,
                    )
                    for header in config.http_retry.headers or []
                ],
            )
            if config.http_retry
            else None,
            tcp_connection_pool=TcpConnectionPoolArgs(
                max_connections=config.tcp_connection_pool.max_connections,
            )
            if config.tcp_connection_pool
            else None,
            tcp_retry_policy=TcpRetryPolicyArgs(
                max_connect_attempts=config.tcp_retries.max_retries,
            )
            if config.tcp_retries
            else None,
            timeout_policy=TimeoutPolicyArgs(
                connection_timeout_in_seconds=config.timeout.connection_timeout_seconds,
                response_timeout_in_seconds=config.timeout.response_timeout_seconds,
            )
            if config.timeout
            else None,
        ),
        opts=opts,
    )

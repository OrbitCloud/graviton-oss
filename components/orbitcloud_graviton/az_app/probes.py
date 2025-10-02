from typing import Literal

from pulumi_azure_native import app
from pydantic import BaseModel, ConfigDict, Field, model_validator


class HttpProbe(BaseModel):
    port: int
    host: str | None = None
    path: str
    scheme: app.Scheme = app.Scheme.HTTP
    headers: dict[str, str] | None = None

    def args(self) -> app.ContainerAppProbeHttpGetArgs:
        return app.ContainerAppProbeHttpGetArgs(
            port=self.port,
            host=self.host,
            path=self.path,
            scheme=self.scheme,
            http_headers=[
                app.ContainerAppProbeHttpHeadersArgs(name=k, value=v)
                for k, v in self.headers.items()
            ]
            if self.headers
            else None,
        )


class TcpProbe(BaseModel):
    port: int
    host: str | None = None

    def args(self) -> app.ContainerAppProbeTcpSocketArgs:
        return app.ContainerAppProbeTcpSocketArgs(port=self.port)


class ContainerProbeConfig(BaseModel):
    probe_type: Literal["Liveness", "Readiness", "Startup"] = Field(
        default="Liveness", description="The type of probe."
    )

    http: HttpProbe | None = None
    tcp: TcpProbe | None = None

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

    @model_validator(mode="after")
    def one_probe_type(m: "ContainerProbeConfig") -> "ContainerProbeConfig":
        if not m.http and not m.tcp:
            raise ValueError("One of http or tcp probes must be defined")
        return m

    def args(self) -> app.ContainerAppProbeArgs:
        return app.ContainerAppProbeArgs(
            type=self.probe_type,
            http_get=self.http.args() if self.http else None,
            tcp_socket=self.tcp.args() if self.tcp else None,
            initial_delay_seconds=self.initial_delay_seconds,
            period_seconds=self.interval_seconds,
            success_threshold=self.success_threshold,
            failure_threshold=self.failure_threshold,
            timeout_seconds=self.timeout_seconds,
        )

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

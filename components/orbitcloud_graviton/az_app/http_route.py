import pulumi
from pulumi_azure_native import app
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .ingress import CustomDomainConfig


class HttpRouteMatchConfig(BaseModel):
    """Match condition for an HTTP route. Exactly one of path, prefix, or
    path_separated_prefix must be set."""

    path: str | None = None
    prefix: str | None = None
    path_separated_prefix: str | None = None
    case_sensitive: bool | None = None

    @model_validator(mode="after")
    def exactly_one_match(m: "HttpRouteMatchConfig") -> "HttpRouteMatchConfig":
        set_count = sum(
            1
            for field in ["path", "prefix", "path_separated_prefix"]
            if getattr(m, field) is not None
        )
        if set_count != 1:
            raise ValueError(
                "Exactly one of 'path', 'prefix', 'path_separated_prefix' must be set."
            )
        return m

    model_config = ConfigDict(extra="forbid")


class HttpRouteActionConfig(BaseModel):
    """Action to perform on a matched HTTP route."""

    prefix_rewrite: str | None = None

    model_config = ConfigDict(extra="forbid")


class HttpRouteTargetConfig(BaseModel):
    """Target container app for an HTTP route rule."""

    container_app: str
    revision: str | None = None
    label: str | None = None
    weight: int | None = Field(default=None, ge=0, le=100)

    model_config = ConfigDict(extra="forbid")


class HttpRouteEntry(BaseModel):
    """A single route entry combining a match condition and an optional action."""

    match: HttpRouteMatchConfig
    action: HttpRouteActionConfig | None = None

    model_config = ConfigDict(extra="forbid")


class HttpRouteRuleConfig(BaseModel):
    """A rule with match conditions (routes) and targets."""

    description: str | None = None
    routes: list[HttpRouteEntry] | None = None
    targets: list[HttpRouteTargetConfig] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_target_weights(m: "HttpRouteRuleConfig") -> "HttpRouteRuleConfig":
        if len(m.targets) > 1:
            weights = [t.weight for t in m.targets]
            if all(w is not None for w in weights):
                total = sum(weights)  # type: ignore[arg-type]
                if total != 100:
                    raise ValueError(
                        f"Target weights must sum to 100 when all targets specify weights, got {total}."
                    )
        return m

    model_config = ConfigDict(extra="forbid")


class HttpRouteConfigModel(BaseModel):
    """Top-level HTTP route configuration model."""

    # Azure requires httpRouteName to match ^[a-z][a-z0-9]*$ (lowercase
    # alphanumeric, starting with a letter — no hyphens). Validating here
    # surfaces the error at config load instead of at deploy time.
    name: str = Field(..., pattern=r"^[a-z][a-z0-9]*$")
    custom_domains: list[CustomDomainConfig] | None = None
    rules: list[HttpRouteRuleConfig] = Field(..., min_length=1)

    model_config = ConfigDict(extra="forbid")


def build_http_route_config(
    environment_name: str | pulumi.Output[str],
    resource_group_name: str | pulumi.Output[str],
    config: HttpRouteConfigModel,
    opts: pulumi.ResourceOptions | None = None,
) -> app.HttpRouteConfig:
    """Create an Azure Container Apps HttpRouteConfig Pulumi resource."""

    rules_args: list[app.HttpRouteRuleArgs] = []
    for rule in config.rules:
        route_args: list[app.HttpRouteArgs] | None = None
        if rule.routes:
            route_args = [
                app.HttpRouteArgs(
                    match=app.HttpRouteMatchArgs(
                        path=entry.match.path,
                        prefix=entry.match.prefix,
                        path_separated_prefix=entry.match.path_separated_prefix,
                        case_sensitive=entry.match.case_sensitive,
                    ),
                    action=app.HttpRouteActionArgs(
                        prefix_rewrite=entry.action.prefix_rewrite,
                    )
                    if entry.action
                    else None,
                )
                for entry in rule.routes
            ]

        target_args: list[app.HttpRouteTargetArgs] = [
            app.HttpRouteTargetArgs(
                container_app=target.container_app,
                revision=target.revision,
                label=target.label,
                weight=target.weight,
            )
            for target in rule.targets
        ]

        rules_args.append(
            app.HttpRouteRuleArgs(
                description=rule.description,
                routes=route_args,
                targets=target_args,
            )
        )

    custom_domain_args: list[app.CustomDomainArgs] | None = None
    if config.custom_domains:
        custom_domain_args = [
            app.CustomDomainArgs(
                name=domain.name,
                certificate_id=domain.certificate_id,
                binding_type=domain.ssl,
            )
            for domain in config.custom_domains
        ]

    return app.HttpRouteConfig(
        resource_name=config.name,
        args=app.HttpRouteConfigArgs(
            http_route_name=config.name,
            environment_name=environment_name,
            resource_group_name=resource_group_name,
            properties=app.HttpRouteConfigPropertiesArgs(
                rules=rules_args,
                custom_domains=custom_domain_args,
            ),
        ),
        opts=opts,
    )

import pulumi
from pulumi_azure_native import app
from pydantic import BaseModel, ConfigDict, Field, model_validator

from orbitcloud_graviton.az_network import DnsZone, DnsZoneConfig
from orbitcloud_graviton.az_network.dns_zone import DnsZoneStack
from orbitcloud_graviton.az_network.types import CnameRecord, TxtRecord
from orbitcloud_graviton.pulumi_lib import AzureStack

from .certificate import managed_certificate
from .ingress import CustomDomainConfig
from .outputs import ContainerAppEnvOutput


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


def _setup_route_custom_domain(
    stack: AzureStack,
    env_output: ContainerAppEnvOutput,
    route_config: app.HttpRouteConfig,
    domain: CustomDomainConfig,
) -> app.ManagedCertificate | None:
    """Wire up DNS records and a managed certificate for a route config custom
    domain, mirroring the container app ingress path. The CNAME points at the
    route config's own FQDN; domain ownership is proven with the environment's
    verification id. Returns the managed certificate when ``ssl: Auto`` is set."""
    zone = None
    if domain.dns_zone_stack:
        dns_stack: DnsZoneStack = DnsZoneStack.model_validate(obj=domain.dns_zone_stack)

        if not domain.name.endswith(f".{dns_stack.name}"):
            raise ValueError(
                f"Mismatch between domain name and DNS zone name: {domain.name} is not a subdomain of {dns_stack.name}"
            )

        relative_name: str = domain.name.removesuffix(f".{dns_stack.name}")

        zone = DnsZone(
            dns_zone_id=str(object=dns_stack.id),
            config=DnsZoneConfig(
                name=dns_stack.name,
                records=[
                    CnameRecord(
                        relative_name=relative_name,
                        value=route_config.properties.fqdn,
                    ),
                    TxtRecord(
                        relative_name=f"asuid.{relative_name}",
                        values=[env_output.custom_domain_verification_id],
                    ),
                ],
            ),
            stack=AzureStack(
                subscription_id=dns_stack.id.subscription_id,
                resource_group_name=dns_stack.id.resource_group_name,
                location=stack.location,
                tenant_id=stack.tenant_id,
                env=stack.env,
                workload_name=stack.workload_name,
            ),
            opts=pulumi.ResourceOptions(parent=route_config),
        )

    if domain.ssl == app.BindingType.AUTO:
        return managed_certificate(
            stack=stack,
            custom_domain=domain.name,
            environment=env_output,
            managed_certificate_name=domain.managed_certificate_name,
            opts=pulumi.ResourceOptions(
                parent=route_config, depends_on=zone.records if zone else None
            ),
        )

    return None


def _route_endpoint_exports(
    route_config: app.HttpRouteConfig,
    config: HttpRouteConfigModel,
) -> dict[str, object]:
    """Build the stack-export payload for a route config endpoint, mirroring the
    container app ``endpoints`` shape: the route's own FQDN as ``default`` plus
    any configured custom domains, each as an ``https://`` URL."""
    return {
        "endpoints": {
            "default": route_config.properties.fqdn.apply(
                lambda fqdn: f"https://{fqdn}" if fqdn else None
            ),
            "custom_domains": [f"https://{domain.name}" for domain in config.custom_domains]
            if config.custom_domains
            else [],
        },
    }


def build_http_route_config(
    stack: AzureStack,
    env_output: ContainerAppEnvOutput,
    config: HttpRouteConfigModel,
    opts: pulumi.ResourceOptions | None = None,
) -> app.HttpRouteConfig:
    """Create an Azure Container Apps HttpRouteConfig Pulumi resource.

    When a custom domain sets ``dns_zone_stack`` and/or ``ssl: Auto``, the
    matching DNS records and managed certificate are created automatically,
    the same way ingress custom domains are handled on container apps.
    """

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

    route_config = app.HttpRouteConfig(
        resource_name=config.name,
        args=app.HttpRouteConfigArgs(
            http_route_name=config.name,
            environment_name=env_output.name,
            resource_group_name=env_output.resource_group_name,
            properties=app.HttpRouteConfigPropertiesArgs(
                rules=rules_args,
                custom_domains=custom_domain_args,
            ),
        ),
        opts=opts,
    )

    for domain in config.custom_domains or []:
        _setup_route_custom_domain(
            stack=stack,
            env_output=env_output,
            route_config=route_config,
            domain=domain,
        )

    stack.export(
        prefix=f"http_route_{config.name}",
        exports=_route_endpoint_exports(route_config=route_config, config=config),
    )

    return route_config

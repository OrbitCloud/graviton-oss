"""Azure Front Door (Standard/Premium) component.

Wraps a ``Microsoft.Cdn`` profile together with its endpoints, origin groups,
origins, custom domains, routes and -- on Premium -- a WAF security policy.
"""

from enum import StrEnum

import pulumi
from pulumi_azure_native import cdn, monitor
from pydantic import BaseModel, ConfigDict, Field

from orbitcloud_graviton.az_lib.types import AzureIdRef
from orbitcloud_graviton.az_monitor import diagnostic_setting
from orbitcloud_graviton.pulumi_lib import AzureStack

LOG_CATEGORIES: list[str] = [
    "FrontDoorAccessLog",
    "FrontDoorHealthProbeLog",
    "FrontDoorWebApplicationFirewallLog",
]


class FrontDoorSku(StrEnum):
    STANDARD = cdn.SkuName.STANDARD_AZURE_FRONT_DOOR
    PREMIUM = cdn.SkuName.PREMIUM_AZURE_FRONT_DOOR


class FrontDoorOriginConfig(BaseModel):
    name: str
    host_name: str
    origin_host_header: str | None = None
    http_port: int = 80
    https_port: int = 443
    priority: int = Field(default=1, ge=1, le=5)
    weight: int = Field(default=1000, ge=1, le=1000)
    enabled: bool = True
    enforce_certificate_name_check: bool = True
    # Private Link origin (Premium only)
    private_link_resource_id: AzureIdRef | None = None
    private_link_location: str | None = None
    private_link_request_message: str | None = None
    private_link_group_id: str | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class FrontDoorHealthProbeConfig(BaseModel):
    path: str = "/"
    protocol: cdn.ProbeProtocol = cdn.ProbeProtocol.HTTPS
    request_type: cdn.HealthProbeRequestType = cdn.HealthProbeRequestType.HEAD
    interval_seconds: int = Field(default=100, ge=1)

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class FrontDoorLoadBalancingConfig(BaseModel):
    sample_size: int = 4
    successful_samples_required: int = 3
    additional_latency_milliseconds: int = 50

    model_config = ConfigDict(extra="forbid")


class FrontDoorOriginGroupConfig(BaseModel):
    name: str
    origins: list[FrontDoorOriginConfig]
    health_probe: FrontDoorHealthProbeConfig | None = Field(
        default_factory=FrontDoorHealthProbeConfig
    )
    load_balancing: FrontDoorLoadBalancingConfig = Field(
        default_factory=FrontDoorLoadBalancingConfig
    )
    session_affinity: bool = False

    model_config = ConfigDict(extra="forbid")


class FrontDoorCustomDomainConfig(BaseModel):
    name: str
    host_name: str
    dns_zone_id: AzureIdRef | None = None
    certificate_type: cdn.AfdCertificateType = cdn.AfdCertificateType.MANAGED_CERTIFICATE
    certificate_secret_id: AzureIdRef | None = None
    minimum_tls_version: cdn.AfdMinimumTlsVersion = cdn.AfdMinimumTlsVersion.TLS12

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class FrontDoorRouteConfig(BaseModel):
    name: str
    origin_group: str
    patterns_to_match: list[str] = Field(default_factory=lambda: ["/*"])
    supported_protocols: list[cdn.AFDEndpointProtocols] = Field(
        default_factory=lambda: [cdn.AFDEndpointProtocols.HTTP, cdn.AFDEndpointProtocols.HTTPS]
    )
    forwarding_protocol: cdn.ForwardingProtocol = cdn.ForwardingProtocol.HTTPS_ONLY
    https_redirect: bool = True
    link_to_default_domain: bool = True
    custom_domains: list[str] | None = None
    origin_path: str | None = None
    enabled: bool = True

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class FrontDoorEndpointConfig(BaseModel):
    name: str
    enabled: bool = True
    routes: list[FrontDoorRouteConfig] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class FrontDoorConfig(BaseModel):
    name: str | None = None
    sku: FrontDoorSku = FrontDoorSku.STANDARD
    origin_response_timeout_seconds: int = Field(default=60, ge=16, le=240)

    endpoints: list[FrontDoorEndpointConfig] = Field(default_factory=list)
    origin_groups: list[FrontDoorOriginGroupConfig] = Field(default_factory=list)
    custom_domains: list[FrontDoorCustomDomainConfig] = Field(default_factory=list)

    # WAF -- Premium SKU only
    waf_policy_id: AzureIdRef | None = None
    waf_patterns_to_match: list[str] = Field(default_factory=lambda: ["/*"])

    log_workspace_id: AzureIdRef | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class FrontDoor(pulumi.ComponentResource):
    """An Azure Front Door Standard/Premium profile and its child resources."""

    def __init__(
        self,
        stack: AzureStack,
        config: FrontDoorConfig,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        self.stack: AzureStack = stack
        self.config: FrontDoorConfig = config

        self._validate()

        super().__init__(
            "Graviton:FrontDoor",
            name=f"afd-{config.name or stack.workload_name}-{stack.env}",
            props=None,
            opts=opts,
        )

        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts1=opts, opts2=pulumi.ResourceOptions(parent=self)
        )

        self.profile: cdn.Profile = self._profile()
        self.origin_groups: dict[str, cdn.AFDOriginGroup] = self._origin_groups()
        self.origins: dict[str, cdn.AFDOrigin] = self._origins()
        self.custom_domains: dict[str, cdn.AFDCustomDomain] = self._custom_domains()
        self.endpoints: dict[str, cdn.AFDEndpoint] = self._endpoints()
        self.routes: dict[str, cdn.Route] = self._routes()
        self.security_policy: cdn.SecurityPolicy | None = self._security_policy()
        self.diagnostic_settings: monitor.DiagnosticSetting | None = self._diagnostic_settings()

        self._outputs()

    @property
    def name(self) -> pulumi.Output[str]:
        return self.profile.name

    @property
    def id(self) -> pulumi.Output[str]:
        return self.profile.id

    def _validate(self) -> None:
        group_names: set[str] = {group.name for group in self.config.origin_groups}
        domain_names: set[str] = {domain.name for domain in self.config.custom_domains}

        for endpoint in self.config.endpoints:
            for route in endpoint.routes:
                if route.origin_group not in group_names:
                    raise ValueError(
                        f"Route '{route.name}' references unknown origin group "
                        f"'{route.origin_group}'"
                    )
                for domain in route.custom_domains or []:
                    if domain not in domain_names:
                        raise ValueError(
                            f"Route '{route.name}' references unknown custom domain '{domain}'"
                        )

        if self.config.waf_policy_id and self.config.sku is not FrontDoorSku.PREMIUM:
            raise ValueError("A WAF security policy requires the Premium_AzureFrontDoor SKU")

    def _profile_name(self) -> str:
        return self.stack.name_for(
            resource_type=cdn.Profile,
            workload_name=self.config.name or self.stack.workload_name,
        )

    def _profile(self) -> cdn.Profile:
        profile_name: str = self._profile_name()

        return cdn.Profile(
            resource_name=profile_name,
            args=cdn.ProfileArgs(
                profile_name=profile_name,
                resource_group_name=self.stack.resource_group.name,
                # AFD profiles are always global, regardless of the stack location.
                location="global",
                tags=self.stack.tags,
                sku=cdn.SkuArgs(name=self.config.sku),
                origin_response_timeout_seconds=self.config.origin_response_timeout_seconds,
            ),
            opts=self._opts,
        )

    def _origin_groups(self) -> dict[str, cdn.AFDOriginGroup]:
        return {
            group.name: cdn.AFDOriginGroup(
                resource_name=self.stack.name_for(
                    resource_type=cdn.AFDOriginGroup, workload_name=group.name
                ),
                args=cdn.AFDOriginGroupArgs(
                    origin_group_name=group.name,
                    profile_name=self.profile.name,
                    resource_group_name=self.stack.resource_group.name,
                    session_affinity_state=cdn.EnabledState.ENABLED
                    if group.session_affinity
                    else cdn.EnabledState.DISABLED,
                    load_balancing_settings=cdn.LoadBalancingSettingsParametersArgs(
                        sample_size=group.load_balancing.sample_size,
                        successful_samples_required=group.load_balancing.successful_samples_required,
                        additional_latency_in_milliseconds=group.load_balancing.additional_latency_milliseconds,
                    ),
                    health_probe_settings=cdn.HealthProbeParametersArgs(
                        probe_path=group.health_probe.path,
                        probe_protocol=group.health_probe.protocol,
                        probe_request_type=group.health_probe.request_type,
                        probe_interval_in_seconds=group.health_probe.interval_seconds,
                    )
                    if group.health_probe
                    else None,
                ),
                opts=pulumi.ResourceOptions.merge(
                    opts1=self._opts, opts2=pulumi.ResourceOptions(parent=self.profile)
                ),
            )
            for group in self.config.origin_groups
        }

    def _origins(self) -> dict[str, cdn.AFDOrigin]:
        origins: dict[str, cdn.AFDOrigin] = {}

        for group in self.config.origin_groups:
            origin_group: cdn.AFDOriginGroup = self.origin_groups[group.name]

            for origin in group.origins:
                origins[origin.name] = cdn.AFDOrigin(
                    resource_name=self.stack.name_for(
                        resource_type=cdn.AFDOrigin, workload_name=origin.name
                    ),
                    args=cdn.AFDOriginArgs(
                        origin_name=origin.name,
                        origin_group_name=origin_group.name,
                        profile_name=self.profile.name,
                        resource_group_name=self.stack.resource_group.name,
                        host_name=origin.host_name,
                        origin_host_header=origin.origin_host_header or origin.host_name,
                        http_port=origin.http_port,
                        https_port=origin.https_port,
                        priority=origin.priority,
                        weight=origin.weight,
                        enabled_state=cdn.EnabledState.ENABLED
                        if origin.enabled
                        else cdn.EnabledState.DISABLED,
                        enforce_certificate_name_check=origin.enforce_certificate_name_check,
                        shared_private_link_resource=self._private_link(origin),
                    ),
                    opts=pulumi.ResourceOptions.merge(
                        opts1=self._opts, opts2=pulumi.ResourceOptions(parent=origin_group)
                    ),
                )

        return origins

    @staticmethod
    def _private_link(
        origin: FrontDoorOriginConfig,
    ) -> cdn.SharedPrivateLinkResourcePropertiesArgs | None:
        if not origin.private_link_resource_id:
            return None

        return cdn.SharedPrivateLinkResourcePropertiesArgs(
            private_link=cdn.ResourceReferenceArgs(id=str(origin.private_link_resource_id)),
            private_link_location=origin.private_link_location,
            group_id=origin.private_link_group_id,
            request_message=origin.private_link_request_message,
        )

    def _custom_domains(self) -> dict[str, cdn.AFDCustomDomain]:
        return {
            domain.name: cdn.AFDCustomDomain(
                resource_name=self.stack.name_for(
                    resource_type=cdn.AFDCustomDomain, workload_name=domain.name
                ),
                args=cdn.AFDCustomDomainArgs(
                    custom_domain_name=domain.name,
                    profile_name=self.profile.name,
                    resource_group_name=self.stack.resource_group.name,
                    host_name=domain.host_name,
                    azure_dns_zone=cdn.ResourceReferenceArgs(id=str(domain.dns_zone_id))
                    if domain.dns_zone_id
                    else None,
                    tls_settings=cdn.AFDDomainHttpsParametersArgs(
                        certificate_type=domain.certificate_type,
                        minimum_tls_version=domain.minimum_tls_version,
                        secret=cdn.ResourceReferenceArgs(id=str(domain.certificate_secret_id))
                        if domain.certificate_secret_id
                        else None,
                    ),
                ),
                opts=pulumi.ResourceOptions.merge(
                    opts1=self._opts, opts2=pulumi.ResourceOptions(parent=self.profile)
                ),
            )
            for domain in self.config.custom_domains
        }

    def _endpoints(self) -> dict[str, cdn.AFDEndpoint]:
        return {
            endpoint.name: cdn.AFDEndpoint(
                resource_name=self.stack.name_for(
                    resource_type=cdn.AFDEndpoint, workload_name=endpoint.name
                ),
                args=cdn.AFDEndpointArgs(
                    endpoint_name=endpoint.name,
                    profile_name=self.profile.name,
                    resource_group_name=self.stack.resource_group.name,
                    location="global",
                    tags=self.stack.tags,
                    enabled_state=cdn.EnabledState.ENABLED
                    if endpoint.enabled
                    else cdn.EnabledState.DISABLED,
                ),
                opts=pulumi.ResourceOptions.merge(
                    opts1=self._opts, opts2=pulumi.ResourceOptions(parent=self.profile)
                ),
            )
            for endpoint in self.config.endpoints
        }

    def _routes(self) -> dict[str, cdn.Route]:
        routes: dict[str, cdn.Route] = {}

        for endpoint in self.config.endpoints:
            afd_endpoint: cdn.AFDEndpoint = self.endpoints[endpoint.name]

            for route in endpoint.routes:
                routes[route.name] = cdn.Route(
                    resource_name=self.stack.name_for(
                        resource_type=cdn.Route, workload_name=route.name
                    ),
                    args=cdn.RouteArgs(
                        route_name=route.name,
                        endpoint_name=afd_endpoint.name,
                        profile_name=self.profile.name,
                        resource_group_name=self.stack.resource_group.name,
                        origin_group=cdn.ResourceReferenceArgs(
                            id=self.origin_groups[route.origin_group].id
                        ),
                        origin_path=route.origin_path,
                        patterns_to_match=route.patterns_to_match,
                        supported_protocols=route.supported_protocols,
                        forwarding_protocol=route.forwarding_protocol,
                        https_redirect=cdn.HttpsRedirect.ENABLED
                        if route.https_redirect
                        else cdn.HttpsRedirect.DISABLED,
                        link_to_default_domain=cdn.LinkToDefaultDomain.ENABLED
                        if route.link_to_default_domain
                        else cdn.LinkToDefaultDomain.DISABLED,
                        custom_domains=[
                            cdn.ActivatedResourceReferenceArgs(
                                id=self.custom_domains[domain].id,
                            )
                            for domain in route.custom_domains or []
                        ],
                        enabled_state=cdn.EnabledState.ENABLED
                        if route.enabled
                        else cdn.EnabledState.DISABLED,
                    ),
                    opts=pulumi.ResourceOptions.merge(
                        opts1=self._opts,
                        opts2=pulumi.ResourceOptions(
                            parent=afd_endpoint,
                            depends_on=list(self.origins.values()),
                        ),
                    ),
                )

        return routes

    def _security_policy(self) -> cdn.SecurityPolicy | None:
        if not self.config.waf_policy_id:
            return None

        domains: list[cdn.ActivatedResourceReferenceArgs] = [
            cdn.ActivatedResourceReferenceArgs(id=domain.id)
            for domain in self.custom_domains.values()
        ] + [
            cdn.ActivatedResourceReferenceArgs(id=endpoint.id)
            for endpoint in self.endpoints.values()
        ]

        if not domains:
            raise ValueError("A WAF security policy needs at least one endpoint or custom domain")

        policy_name = f"{self._profile_name()}-waf"

        return cdn.SecurityPolicy(
            resource_name=policy_name,
            args=cdn.SecurityPolicyArgs(
                security_policy_name=policy_name,
                profile_name=self.profile.name,
                resource_group_name=self.stack.resource_group.name,
                parameters=cdn.SecurityPolicyWebApplicationFirewallParametersArgs(
                    type="WebApplicationFirewall",
                    waf_policy=cdn.ResourceReferenceArgs(id=str(self.config.waf_policy_id)),
                    associations=[
                        cdn.SecurityPolicyWebApplicationFirewallAssociationArgs(
                            domains=domains,
                            patterns_to_match=self.config.waf_patterns_to_match,
                        )
                    ],
                ),
            ),
            opts=pulumi.ResourceOptions.merge(
                opts1=self._opts, opts2=pulumi.ResourceOptions(parent=self.profile)
            ),
        )

    def _diagnostic_settings(self) -> monitor.DiagnosticSetting | None:
        if not self.config.log_workspace_id:
            return None

        return diagnostic_setting(
            resource=self.profile,
            log_workspace_id=str(self.config.log_workspace_id),
            metric_categories=["AllMetrics"],
            log_categories=LOG_CATEGORIES,
            opts=pulumi.ResourceOptions(parent=self.profile),
        )

    def _outputs(self) -> None:
        self.register_outputs(
            {
                "profile": self.profile,
                "endpoints": self.endpoints,
            }
        )

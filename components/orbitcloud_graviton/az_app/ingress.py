from typing import Literal

import pulumi
from pulumi_azure_native.app import v20241002preview as app
from pydantic import BaseModel, ConfigDict, Field, model_validator

from orbitcloud_graviton.az_lib.types import AzureIdRef, StrRef
from orbitcloud_graviton.az_network.types import PrivateIPv4Network, PublicIPv4Network

from .cors import AppCorsConfig


class CustomDomainConfig(BaseModel):
    name: str
    certificate_id: AzureIdRef | None = None
    ssl: app.BindingType | None = app.BindingType.SNI_ENABLED
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class AdditionalTcpIngress(BaseModel):
    target_port: int
    exposed_port: int | None = None
    external: bool = False

    def args(self) -> app.IngressPortMappingArgs:
        return app.IngressPortMappingArgs(
            target_port=self.target_port,
            exposed_port=self.exposed_port,
            external=self.external,
        )

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class HttpIngressConfig(BaseModel):
    protocol: Literal["http"]
    client_certificate_mode: app.IngressClientCertificateMode = (
        app.IngressClientCertificateMode.IGNORE
    )

    target_port: int
    external: bool | None = False
    ip_allow_list: list[PrivateIPv4Network | PublicIPv4Network | StrRef] | None = None

    additional_tcp_ingress: list[AdditionalTcpIngress] | None = None

    custom_domains: list[CustomDomainConfig] | None = None
    https_only: bool | None = True
    cors: AppCorsConfig | None = None
    sticky_sessions: app.Affinity | None = app.Affinity.NONE

    def args(self) -> app.IngressArgs:
        return app.IngressArgs(
            allow_insecure=not self.https_only,
            external=self.external,
            target_port=self.target_port,
            custom_domains=[
                app.CustomDomainArgs(
                    name=domain.name,
                    certificate_id=domain.certificate_id,
                    binding_type=domain.ssl,
                )
                for domain in self.custom_domains
            ]
            if self.custom_domains
            else None,
            client_certificate_mode=self.client_certificate_mode,
            sticky_sessions=app.IngressStickySessionsArgs(
                affinity=self.sticky_sessions,
            ),
            transport=app.IngressTransportMethod.TCP
            if self.protocol == "tcp"
            else app.IngressTransportMethod.AUTO,
            ip_security_restrictions=[
                app.IpSecurityRestrictionRuleArgs(
                    name=f"allow-{ip}",
                    action=app.Action.ALLOW,
                    ip_address_range=str(object=ip),
                )
                for ip in self.ip_allow_list or []
            ],
            cors_policy=self.cors.cors_policy_args() if self.cors else None,
            additional_port_mappings=[
                port_mapping.args() for port_mapping in self.additional_tcp_ingress
            ]
            if self.additional_tcp_ingress
            else None,
        )

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class TcpIngressConfig(BaseModel):
    protocol: Literal["tcp"]
    target_port: int
    exposed_port: int | None = None
    external: bool | None = False
    additional_tcp_ingress: list[AdditionalTcpIngress] | None = None
    custom_domains: list[CustomDomainConfig] | None = None
    ip_allow_list: list[PrivateIPv4Network | PublicIPv4Network | StrRef] | None = Field(
        default_factory=list
    )

    def args(self) -> app.IngressArgs:
        return app.IngressArgs(
            allow_insecure=False,
            external=self.external,
            target_port=self.target_port,
            custom_domains=[
                app.CustomDomainArgs(
                    name=domain.name,
                    certificate_id=domain.certificate_id,
                    binding_type=domain.ssl,
                )
                for domain in (self.custom_domains or [])
            ],
            transport=app.IngressTransportMethod.TCP,
            ip_security_restrictions=[
                app.IpSecurityRestrictionRuleArgs(
                    name=f"allow-{ip}",
                    action=app.Action.ALLOW,
                    ip_address_range=str(object=ip),
                )
                for ip in self.ip_allow_list or []
            ],
            additional_port_mappings=[
                port_mapping.args() for port_mapping in self.additional_tcp_ingress or []
            ],
        )

    @model_validator(mode="after")
    def validate_exposed_port(m: "TcpIngressConfig") -> "TcpIngressConfig":
        if (m.external and m.exposed_port) and not m.ip_allow_list:
            pulumi.warn(
                msg="External TCP ingress is configured without IP allow list. Are you sure?"
            )
        return m

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

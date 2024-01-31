from typing import Optional
from uuid import UUID

import pulumi
from pulumi import ComponentResource
from pulumi_azure_native.network import v20230901 as network
from pydantic import BaseModel, ConfigDict, HttpUrl, field_validator

from orbitcloud_graviton.pulumi_lib import get_azure_stack

from ._types import PrivateIPv4Network


class P2SVpnEntraAuthConfig(BaseModel):
    entra_tenant: HttpUrl
    entra_issuer: HttpUrl
    entra_audience: UUID

    @field_validator("entra_issuer")
    def has_trailing_slash(cls, v: HttpUrl) -> HttpUrl:
        if not str(v).endswith("/"):
            raise ValueError("AAD Issuer must end with a trailing slash (Azure docs)")
        return v


class P2SVpnCertAuthConfig(BaseModel):
    client_root_cert: str


class P2sVpnGwConfig(BaseModel):
    client_address_pool: PrivateIPv4Network
    entra_auth: Optional[P2SVpnEntraAuthConfig] = None
    cert_auth: Optional[P2SVpnCertAuthConfig] = None

    # Add validation for either entra_auth or cert_auth
    @field_validator("entra_auth")
    def validate_auth(cls, v, values):
        if not v and not values.get("cert_auth"):
            raise ValueError("Either entra_auth or cert_auth must be set")
        return v

    model_config = ConfigDict(arbitrary_types_allowed=True)


class P2sVpnGw(ComponentResource):
    def __init__(
        self,
        config: P2sVpnGwConfig,
        vhub: network.VirtualHub,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        self.stack = get_azure_stack()
        super().__init__(
            "Graviton:az_network:P2sVpnGw", name=f"vpngw-{self.stack.workload_name}", props=None, opts=opts
        )
        self._opts = pulumi.ResourceOptions.merge(pulumi.ResourceOptions(parent=self), opts)

        self.config = config
        self._vhub = vhub

        self.server_config = self._server_config()
        self.p2s_vpngw = self._p2s_vpngw()

        self._outputs()

    def _outputs(self) -> None:
        self.outputs = {
            "resource_group_name": self.stack.resource_group.name,
            "resource_group_id": self.stack.resource_group.id,
            "p2s_vpngw_id": self.p2s_vpngw.id,
        }
        self.register_outputs(self.outputs)

    def _server_config(self) -> network.VpnServerConfiguration:
        auth_types = []
        auth_protocols = []

        if self.config.entra_auth:
            auth_types.append("AAD")
            auth_protocols.append("OpenVPN")

        if self.config.cert_auth:
            auth_types.append("Certificate")
            auth_protocols.append("IKEv2")

        return network.VpnServerConfiguration(
            resource_name=self.stack.name_for(network.VpnServerConfiguration),
            vpn_server_configuration_name=self.stack.name_for(network.VpnServerConfiguration),
            location=self.stack.location,
            resource_group_name=self.stack.resource_group.name,
            aad_authentication_parameters=network.AadAuthenticationParametersArgs(
                aad_tenant=str(self.config.entra_auth.entra_tenant),
                aad_issuer=str(self.config.entra_auth.entra_issuer),
                aad_audience=str(self.config.entra_auth.entra_audience),
            )
            if self.config.entra_auth
            else None,
            vpn_authentication_types=auth_types,
            vpn_protocols=auth_protocols,
            vpn_client_root_certificates=[
                network.VpnServerConfigVpnClientRootCertificateArgs(
                    name="p2s-vpngw-client-root-cert",
                    public_cert_data=self.config.cert_auth.client_root_cert,
                )
            ]
            if self.config.cert_auth
            else None,
            opts=self._opts,
        )

    def _p2s_vpngw(self) -> network.P2sVpnGateway:
        return network.P2sVpnGateway(
            resource_name=self.stack.name_for(network.P2sVpnGateway),
            gateway_name=self.stack.name_for(network.P2sVpnGateway),
            location=self.stack.location,
            resource_group_name=self.stack.resource_group.name,
            virtual_hub=network.SubResourceArgs(
                id=self._vhub.id.apply(lambda id: f"{id}"),
            ),
            vpn_gateway_scale_unit=1,
            vpn_server_configuration=network.SubResourceArgs(
                id=self.server_config.id.apply(lambda id: f"{id}"),
            ),
            p2_s_connection_configurations=[
                network.P2SConnectionConfigurationArgs(
                    enable_internet_security=True,
                    name="p2s-vpngw-connection-config",
                    vpn_client_address_pool=network.AddressSpaceArgs(
                        address_prefixes=[str(self.config.client_address_pool)],
                    ),
                )
            ],
            opts=self._opts,
        )

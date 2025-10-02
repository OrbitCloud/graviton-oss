from ipaddress import IPv4Address
from typing import Literal

import pulumi
from pulumi import ComponentResource
from pulumi_azure_native import network
from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from orbitcloud_graviton.az_lib.types import AzureIdRef
from orbitcloud_graviton.pulumi_lib import AzureStack

from .public_ip import PublicIp, PublicIpConfig
from .types import PrivateIPv4Network


class BgpConfig(BaseModel):
    asn: int
    bgp_peering_address: IPv4Address


class S2SConnectionConfig(BaseModel):
    shared_key: SecretStr
    dh_group: Literal[
        "DHGroup1", "DHGroup2", "DHGroup14", "DHGroup2048", "ECP256", "ECP384", "DH_GROUP24"
    ] = "DHGroup14"
    ike_encryption: Literal[
        "DES", "DES3", "AES128", "AES192", "AES256", "GCMAES256", "GCMAES128"
    ] = "GCMAES256"
    ike_integrity: Literal["MD5", "SHA1", "SHA256", "SHA384", "GCMAES256", "GCMAES128"] = "SHA256"
    ipsec_encryption: Literal[
        "DES", "DES3", "AES128", "AES192", "AES256", "GCMAES128", "GCMAES192", "GCMAES256"
    ] = "GCMAES256"
    ipsec_integrity: Literal["MD5", "SHA1", "SHA256", "GCMAES128", "GCMAES192", "GCMAES256"] = (
        "GCMAES256"
    )
    pfs_group: Literal["PFS1", "PFS2", "PFS2048", "ECP256", "ECP384", "PFS24", "PFS14", "PFSMM"] = (
        "PFS14"
    )
    sa_lifetime_seconds: int = 28800
    sa_data_size_kilobytes: int = 0
    dpd_timeout_seconds: int = 45


class S2SConfig(BaseModel):
    fqdn: str | None = None
    public_ip: IPv4Address | None = None
    local_network_address_spaces: list[PrivateIPv4Network] | None = Field(
        default=None,
        title="Local Address Spaces",
        description="One or more IP address ranges (in CIDR notation) that define your local network's (on-prem) address space.",
    )
    traffic_policy_azure_address_ranges: list[PrivateIPv4Network] | None = Field(
        default=None,
        title="Azure Address Ranges",
        description="Represents the IP Ranges of Azure VNET / Subnets that will be reachable from the local network's (on-prem). Used with policy_based_traffic_selectors = true.",
    )
    traffic_policy_local_address_ranges: list[PrivateIPv4Network] | None = Field(
        default=None,
        title="Local Address Ranges",
        description="Represents the IP Ranges of local network's (on-prem) that will be reachable from Azure. Used with policy_based_traffic_selectors = true. Defaults to local_network_address_spaces if not defined.",
    )
    policy_based_traffic_selectors: bool | None = False
    bgp_settings: BgpConfig | None = None
    connection_settings: S2SConnectionConfig

    @model_validator(mode="after")
    def validate_s2s_config(m: "S2SConfig") -> "S2SConfig":
        if not m.public_ip and not m.fqdn:
            raise ValueError("public_ip or fqdn must be defined.")

        if not m.local_network_address_spaces and not m.bgp_settings:
            raise ValueError("local_network_address_space or bgp_settings must be defined.")

        if m.policy_based_traffic_selectors:
            if not m.traffic_policy_local_address_ranges and not m.local_network_address_spaces:
                raise ValueError(
                    "Either traffic_policy_local_address_ranges or local_network_address_spaces must be defined when policy_based_traffic_selectors = true."
                )

            if not m.traffic_policy_azure_address_ranges:
                raise ValueError(
                    "traffic_policy_azure_address_ranges must be defined when policy_based_traffic_selectors = true."
                )

        if not m.policy_based_traffic_selectors:
            if m.traffic_policy_azure_address_ranges or m.traffic_policy_local_address_ranges:
                pulumi.warn(
                    "policy_based_traffic_selectors = false. traffic_policy_azure_address_ranges and traffic_policy_local_address_ranges will be ignored."
                )
        return m


class P2SConfig(BaseModel):
    client_address_pool: PrivateIPv4Network
    entra_auth: bool | None = True
    cert_auth_root_cert: str | None = None

    @model_validator(mode="after")
    def validate_p2s_config(m: "P2SConfig") -> "P2SConfig":
        if not m.entra_auth and not m.cert_auth_root_cert:
            raise ValueError("Either entra_auth or cert_auth must be set")
        return m

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class VirtualNetworkGatewayConfig(BaseModel):
    active_active: bool | None = False
    allow_remote_vnet_traffic: bool | None = False
    public_ips: list[AzureIdRef] | None = (
        None  # TBD: Consider allowing use of pre-created Public IP - (To keep the same public IP during VPN-rebuild)
    )
    subnet: AzureIdRef
    bgp_config: BgpConfig | None = None
    sku: (
        Literal[
            "BASIC",
            "VpnGw1",
            "VpnGw2",
            "VpnGw3",
            "VpnGw4",
            "VpnGw5",
            "VpnGw1AZ",
            "VpnGw2AZ",
            "VpnGw3AZ",
            "VpnGw2AZ",
            "VpnGw3AZ",
            "VpnGw4AZ",
            "VpnGw5AZ",
        ]
        | None
    ) = "VpnGw1"
    site_to_site: S2SConfig | None = None
    point_to_site: P2SConfig | None = None
    gateway_generation: Literal["Generation1", "Generation2"] | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    @model_validator(mode="after")
    def validate_vnet_gateway(m: "VirtualNetworkGatewayConfig") -> "VirtualNetworkGatewayConfig":
        if m.active_active:
            required_ips = 3 if m.point_to_site else 2
            if m.public_ips is not None and len(m.public_ips) != required_ips:
                raise ValueError(
                    "Active-Active requires two public IP. If P2S is enabled, three are required."
                )
            if m.sku == "BASIC":
                raise ValueError("Active-Active is not supported with Basic SKU")
        if m.bgp_config and m.sku == "BASIC":
            raise ValueError("BGP configuration is not supported with Basic SKU")

        # Validate gateway generation and SKU compatibility
        valid_skus = {
            "Generation1": [
                "BASIC",
                "VpnGw1",
                "VpnGw2",
                "VpnGw3",
                "VpnGw1AZ",
                "VpnGw2AZ",
                "VpnGw3AZ",
            ],
            "Generation2": [
                "VpnGw2",
                "VpnGw3",
                "VpnGw4",
                "VpnGw5",
                "VpnGw2AZ",
                "VpnGw3AZ",
                "VpnGw4AZ",
                "VpnGw5AZ",
            ],
        }
        if m.gateway_generation and m.sku not in valid_skus.get(m.gateway_generation, []):
            raise ValueError(
                f"SKU '{m.sku}' is not valid for gateway generation '{m.gateway_generation}'"
            )
        return m


class VirtualNetworkGateway(ComponentResource):
    def __init__(
        self,
        stack: AzureStack,
        config: VirtualNetworkGatewayConfig,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        self.stack: AzureStack = stack
        self.config: VirtualNetworkGatewayConfig = config

        super().__init__(
            "Graviton:az_network:VirtualNetworkGateway",
            name=f"vng-{self.stack.workload_name}",
            props=None,
            opts=opts,
        )
        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts, pulumi.ResourceOptions(parent=self)
        )

        self.public_ips: list[network.PublicIPAddress] = self._public_ips()
        self.vnet_gateway: network.VirtualNetworkGateway = self._vnet_gateway()
        if self.config.site_to_site:
            self.local_network_gateway: network.LocalNetworkGateway | None = (
                self._local_network_gateway()
            )
            self.vnet_connection: network.VirtualNetworkGatewayConnection | None = (
                self._vnet_connection()
            )

        self._outputs()

    def _ipsec_policy(self, ipsec_settings: S2SConnectionConfig) -> network.IpsecPolicyArgs:
        return network.IpsecPolicyArgs(
            dh_group=ipsec_settings.dh_group,
            ike_encryption=ipsec_settings.ike_encryption,
            ike_integrity=ipsec_settings.ike_integrity,
            ipsec_encryption=ipsec_settings.ipsec_encryption,
            ipsec_integrity=ipsec_settings.ipsec_integrity,
            pfs_group=ipsec_settings.pfs_group,
            sa_data_size_kilobytes=ipsec_settings.sa_data_size_kilobytes,
            sa_life_time_seconds=ipsec_settings.sa_lifetime_seconds,
        )

    def _bgp_config(self) -> network.BgpSettingsArgs | None:
        if self.config.bgp_config:
            return network.BgpSettingsArgs(
                asn=self.config.bgp_config.asn,
                bgp_peering_address=str(self.config.bgp_config.bgp_peering_address),
            )
        return None

    def _public_ips(self) -> list[network.PublicIPAddress]:
        # Determine the number of public IPs needed
        if self.config.active_active:
            count = 3 if self.config.point_to_site else 2  # 3 if P2S is configured, otherwise 2
        else:
            count = 1  # Only 1 needed if not active-active

        # Create the public IPs based on the determined count
        return [self._public_ip(i + 1) for i in range(count)]

    def _public_ip(self, index: int) -> network.PublicIPAddress:
        public_ip_config = PublicIpConfig(
            workload=f"vpngateway{index}",
            address_version="IPv4",
            tier="Regional",
        )
        public_ip = PublicIp(
            stack=self.stack,
            config=public_ip_config,
            opts=self._opts,
        )
        return public_ip.public_ip

    def _point_to_site(self) -> network.VpnClientConfigurationArgs | None:
        if not self.config.point_to_site:
            return None

        auth_types = []
        auth_protocols = []

        if self.config.point_to_site.entra_auth:
            auth_types.append("AAD")
            auth_protocols.append("OpenVPN")

        if self.config.point_to_site.cert_auth_root_cert:
            auth_types.append("Certificate")
            auth_protocols.append("IKEv2")

        return network.VpnClientConfigurationArgs(
            aad_tenant=f"https://login.microsoftonline.com/{self.stack.tenant_id}"
            if self.config.point_to_site.entra_auth
            else None,
            aad_issuer=f"https://sts.windows.net/{self.stack.tenant_id}/"
            if self.config.point_to_site.entra_auth
            else None,
            aad_audience="41b23e61-6c1e-4545-b367-cd054e0ed4b4"
            if self.config.point_to_site.entra_auth
            else None,
            vpn_client_address_pool=network.AddressSpaceArgs(
                address_prefixes=[str(self.config.point_to_site.client_address_pool)]
            ),
            vpn_client_root_certificates=[
                network.VpnClientRootCertificateArgs(
                    name="p2s-vpngw-client-root-cert",
                    public_cert_data=self.config.point_to_site.cert_auth_root_cert,
                )
            ]
            if self.config.point_to_site.cert_auth_root_cert
            else None,
            vpn_authentication_types=auth_types,
            vpn_client_protocols=auth_protocols,
        )

    def _vnet_gateway(self) -> network.VirtualNetworkGateway:
        ip_configurations = [
            network.VirtualNetworkGatewayIPConfigurationArgs(
                name=f"ipconfig{i + 1}",
                public_ip_address=network.SubResourceArgs(id=public_ip.id),
                subnet=network.SubResourceArgs(id=self.config.subnet),
            )
            for i, public_ip in enumerate(self.public_ips)
        ]

        return network.VirtualNetworkGateway(
            resource_name=self.stack.name_for(network.VirtualNetworkGateway),
            resource_group_name=self.stack.resource_group.name,
            active_active=self.config.active_active,
            allow_remote_vnet_traffic=self.config.allow_remote_vnet_traffic,
            bgp_settings=self._bgp_config(),
            enable_bgp=True
            if self.config.site_to_site and self.config.site_to_site.bgp_settings
            else None,
            gateway_type=network.VirtualNetworkGatewayType.VPN,
            ip_configurations=ip_configurations,
            location=self.stack.location,
            sku=network.VirtualNetworkGatewaySkuArgs(
                name=self.config.sku,
                tier=self.config.sku,
            ),
            vpn_client_configuration=self._point_to_site(),
            vpn_type=network.VpnType.ROUTE_BASED,
            opts=self._opts,
        )

    def _local_network_gateway(self) -> network.LocalNetworkGateway | None:
        if self.config.site_to_site:
            # Determine BGP settings if configured
            bgp_settings_arg = None
            if self.config.site_to_site.bgp_settings:
                bgp_settings_arg = network.BgpSettingsArgs(
                    asn=self.config.site_to_site.bgp_settings.asn,
                    bgp_peering_address=str(
                        self.config.site_to_site.bgp_settings.bgp_peering_address
                    ),
                )

            # Configure local network address space
            address_prefixes = []
            if self.config.site_to_site.local_network_address_spaces:
                address_prefixes = [
                    str(network)
                    for network in self.config.site_to_site.local_network_address_spaces
                ]

            # Add BGP peering address to address prefixes if BGP is configured
            if self.config.site_to_site.bgp_settings:
                address_prefixes.append(
                    str(self.config.site_to_site.bgp_settings.bgp_peering_address) + "/32"
                )

            # Create the Local Network Gateway
            return network.LocalNetworkGateway(
                resource_name=self.stack.name_for(network.LocalNetworkGateway),
                resource_group_name=self.stack.resource_group.name,
                gateway_ip_address=str(self.config.site_to_site.public_ip)
                if self.config.site_to_site.public_ip
                else None,
                fqdn=self.config.site_to_site.fqdn,
                bgp_settings=bgp_settings_arg,
                local_network_address_space=network.AddressSpaceArgs(
                    address_prefixes=address_prefixes
                ),
                location=self.stack.location,
                opts=self._opts,
            )

    def _vnet_connection(self) -> network.VirtualNetworkGatewayConnection | None:
        if self.vnet_gateway and self.local_network_gateway and self.config.site_to_site:
            # Only add traffic selector policies if policy_based_traffic_selectors = true
            if self.config.site_to_site.policy_based_traffic_selectors:
                # If traffic_policy_local_address_ranges is not defined, use local_network_address_spaces
                remote_address_ranges = (
                    [
                        str(prefix)
                        for prefix in self.config.site_to_site.traffic_policy_local_address_ranges
                    ]
                    if self.config.site_to_site.traffic_policy_local_address_ranges
                    else [
                        str(prefix)
                        for prefix in self.config.site_to_site.local_network_address_spaces
                    ]
                    if self.config.site_to_site.local_network_address_spaces
                    else []
                )
                local_address_ranges = (
                    [
                        str(prefix)
                        for prefix in self.config.site_to_site.traffic_policy_azure_address_ranges
                    ]
                    if self.config.site_to_site.traffic_policy_azure_address_ranges
                    else []
                )
                traffic_selector_policies = network.TrafficSelectorPolicyArgs(
                    local_address_ranges=local_address_ranges,
                    remote_address_ranges=remote_address_ranges,
                )
                traffic_selector_policies = [traffic_selector_policies]
            else:
                traffic_selector_policies = None
            return network.VirtualNetworkGatewayConnection(
                resource_name=self.stack.name_for(network.VirtualNetworkGatewayConnection),
                shared_key=self.config.site_to_site.connection_settings.shared_key.get_secret_value(),
                resource_group_name=self.stack.resource_group.name,
                virtual_network_gateway1=network.VirtualNetworkGatewayArgs(id=self.vnet_gateway.id),
                local_network_gateway2=network.LocalNetworkGatewayArgs(
                    id=self.local_network_gateway.id
                ),
                connection_mode=network.VirtualNetworkGatewayConnectionMode.DEFAULT,
                connection_protocol=network.VirtualNetworkGatewayConnectionProtocol.IK_EV2,
                connection_type=network.VirtualNetworkGatewayConnectionType.IPSEC,
                use_policy_based_traffic_selectors=self.config.site_to_site.policy_based_traffic_selectors,
                dpd_timeout_seconds=self.config.site_to_site.connection_settings.dpd_timeout_seconds,
                traffic_selector_policies=traffic_selector_policies,
                enable_bgp=True if self.config.site_to_site.bgp_settings else None,
                ipsec_policies=[self._ipsec_policy(self.config.site_to_site.connection_settings)],
            )

    def _outputs(self) -> None:
        self.outputs = {
            "vpn_gateway": self.vnet_gateway,
            "vpn_gateway_public_ips": [public_ip.ip_address for public_ip in self.public_ips],
            "vpn_gateway_p2s_client_address_pool": str(
                self.config.point_to_site.client_address_pool
            )
            if self.config.point_to_site
            else None,
        }
        self.register_outputs(self.outputs)

        self.stack.export(
            exports={
                "vpn": {
                    "id": self.vnet_gateway.id,
                    "name": self.vnet_gateway.name,
                    "public_ips": [public_ip.ip_address for public_ip in self.public_ips],
                    "p2s_client_address_pool": str(self.config.point_to_site.client_address_pool)
                    if self.config.point_to_site
                    else None,
                }
            }
        )

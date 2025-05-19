from ipaddress import IPv4Address
from typing import Any, Literal

import pulumi
from pulumi import ComponentResource
from pulumi_azure_native import network
from pydantic import BaseModel, Field, SecretStr, model_validator

from orbitcloud_graviton.pulumi_lib import AzureStack

from .types import PrivateIPv4Network


class S2sVPNConnectionConfig(BaseModel):
    vpn_connection_protocol_type: Literal["IKEv2", "IKEv1"] | None = "IKEv2"
    shared_key: SecretStr
    policy_based_traffic_selector: bool | None = True
    connection_bandwidth: int | None = 1000
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


class SiteLinkConfig(BaseModel):
    name: str
    speed: int | None = 1000
    provider_name: str | None = "provider"
    public_ip: IPv4Address | None = None
    fqdn: str | None = None
    bgp_address: IPv4Address | None = None
    bgp_asn: int | None = None
    connection_settings: S2sVPNConnectionConfig

    @model_validator(mode="after")
    def validate_link_config(m: "SiteLinkConfig") -> "SiteLinkConfig":
        if not m.public_ip and not m.fqdn:
            raise ValueError("public_ip or fqdn must be defined.")
        return m


class S2sVpnSiteConfig(BaseModel):
    name: str
    device_vendor: str | None = "vendor"
    address_prefixes: list[PrivateIPv4Network] | None = Field(
        default=None,
        description="The IP address space that is located on your on-premises site. Traffic destined for this address space is routed to your local site. This is required when BGP isn't enabled for the site.",
        examples=[["192.168.10.0/24"]],
    )
    site_links: list[SiteLinkConfig]
    policy_based_traffic_selectors: bool | None = False
    propagate_default_route: bool | None = False
    traffic_policy_local_address_ranges: list[PrivateIPv4Network] | None = None
    traffic_policy_remote_address_ranges: list[PrivateIPv4Network] | None = None

    @model_validator(mode="after")
    def validate_vpn_site_config(m: "S2sVpnSiteConfig") -> "S2sVpnSiteConfig":
        if not m.address_prefixes:
            for siteLink in m.site_links:
                if not siteLink.bgp_address or not siteLink.bgp_asn:
                    raise ValueError("address_prefixes or BGP address & ASN must be defined.")

        if m.policy_based_traffic_selectors:
            if not m.traffic_policy_local_address_ranges:
                raise ValueError(
                    "traffic_policy_local_address_ranges must be defined when policy_based_traffic_selectors = true."
                )
            if not m.traffic_policy_remote_address_ranges and not m.address_prefixes:
                raise ValueError(
                    "Either traffic_policy_remote_address_ranges or address_prefixes must be defined when policy_based_traffic_selectors = true."
                )

        if not m.policy_based_traffic_selectors:
            if m.traffic_policy_local_address_ranges or m.traffic_policy_remote_address_ranges:
                pulumi.warn(
                    "policy_based_traffic_selectors = false. traffic_policy_local_address_ranges and traffic_policy_remote_address_ranges will be ignored."
                )
        return m


class VwanS2sVpnGatewayConfig(BaseModel):
    scale_unit: int | None = 1
    asn: int | None = 65515
    sites: list[S2sVpnSiteConfig]


class VwanS2SVpnGw(ComponentResource):
    def __init__(
        self,
        stack: AzureStack,
        config: VwanS2sVpnGatewayConfig,
        vhub: network.VirtualHub,
        vwan: network.VirtualWan,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        self.stack: AzureStack = stack
        self.config: VwanS2sVpnGatewayConfig = config

        self._vhub: network.VirtualHub = vhub
        self._vwan: network.VirtualWan = vwan

        self.s2s_sites: list[dict[str, Any]] = self._vpn_sites()
        self.s2s_vpngw: network.VpnGateway = self._s2s_vpngw()

    def _ipsec_policy(self, link_config) -> network.IpsecPolicyArgs:
        return network.IpsecPolicyArgs(
            dh_group=link_config.connection_settings.dh_group,
            ike_encryption=link_config.connection_settings.ike_encryption,
            ike_integrity=link_config.connection_settings.ike_integrity,
            ipsec_encryption=link_config.connection_settings.ipsec_encryption,
            ipsec_integrity=link_config.connection_settings.ipsec_integrity,
            pfs_group=link_config.connection_settings.pfs_group,
            sa_data_size_kilobytes=link_config.connection_settings.sa_data_size_kilobytes,
            sa_life_time_seconds=link_config.connection_settings.sa_lifetime_seconds,
        )

    def _vpn_site_links(self, site_links, site_name) -> list[network.VpnSiteLinkArgs]:
        vpn_site_links = []
        for link in site_links:
            vpn_site_link = network.VpnSiteLinkArgs(
                name=f"link-{site_name}-{link.name}",
                ip_address=str(link.public_ip) if link.public_ip else None,
                fqdn=link.fqdn,
                bgp_properties=network.VpnLinkBgpSettingsArgs(
                    asn=link.bgp_asn,
                    bgp_peering_address=str(link.bgp_address) if link.bgp_address else None,
                )
                if link.bgp_asn and link.bgp_address
                else None,
                link_properties=network.VpnLinkProviderPropertiesArgs(
                    link_provider_name=link.provider_name,
                    link_speed_in_mbps=link.speed,
                ),
            )
            vpn_site_links.append(vpn_site_link)
        return vpn_site_links

    def _vpn_sites(self):
        site_dicts = []
        for site in self.config.sites:
            vpn_site_links = self._vpn_site_links(site.site_links, site.name)
            site_resource = network.VpnSite(
                resource_name=f"vst-{site.name}",
                vpn_site_name=f"vst-{site.name}",
                location=self.stack.location,
                resource_group_name=self.stack.resource_group.name,
                address_space=network.AddressSpaceArgs(
                    address_prefixes=[str(prefix) for prefix in site.address_prefixes]
                    if site.address_prefixes
                    else []
                ),
                virtual_wan=network.SubResourceArgs(id=self._vwan.id),
                vpn_site_links=vpn_site_links,
            )

            site_dicts.append({"site": site_resource, "config": site})
        return site_dicts

    def _s2s_vpngw(self):
        connections = []
        for site_dict in self.s2s_sites:
            site = site_dict["site"]
            site_config = site_dict["config"]

            def create_connection_args(links, site_config=site_config, site=site):
                vpn_site_link_connections = [
                    network.VpnSiteLinkConnectionArgs(
                        name=link_config.name,
                        vpn_site_link=network.SubResourceArgs(id=link.id),
                        connection_bandwidth=link_config.connection_settings.connection_bandwidth,
                        shared_key=link_config.connection_settings.shared_key.get_secret_value(),
                        use_policy_based_traffic_selectors=site_config.policy_based_traffic_selectors,
                        ipsec_policies=[self._ipsec_policy(link_config)],
                    )
                    for link, link_config in zip(links, site_config.site_links, strict=False)
                ]
                # Only add traffic selector policies if policy_based_traffic_selectors = true
                if site_config.policy_based_traffic_selectors:
                    # If traffic_policy_remote_address_ranges is not defined, use address_prefixes
                    remote_address_ranges = (
                        [str(prefix) for prefix in site_config.traffic_policy_remote_address_ranges]
                        if site_config.traffic_policy_remote_address_ranges
                        else [str(prefix) for prefix in site_config.address_prefixes]
                    )
                    local_address_ranges = [
                        str(prefix) for prefix in site_config.traffic_policy_local_address_ranges
                    ]
                    traffic_selector_policies = network.TrafficSelectorPolicyArgs(
                        local_address_ranges=local_address_ranges,
                        remote_address_ranges=remote_address_ranges,
                    )
                    traffic_selector_policies = [traffic_selector_policies]
                else:
                    traffic_selector_policies = None

                return network.VpnConnectionArgs(
                    name=site.name,
                    remote_vpn_site=network.SubResourceArgs(id=site.id),
                    vpn_link_connections=vpn_site_link_connections,
                    enable_internet_security=site_config.propagate_default_route,
                    use_policy_based_traffic_selectors=site_config.policy_based_traffic_selectors,
                    traffic_selector_policies=traffic_selector_policies,
                )

            connection = site.vpn_site_links.apply(create_connection_args)
            connections.append(connection)

        return network.VpnGateway(
            resource_name=self.stack.name_for(network.VpnGateway),
            location=self.stack.location,
            resource_group_name=self.stack.resource_group.name,
            vpn_gateway_scale_unit=self.config.scale_unit,
            virtual_hub=network.SubResourceArgs(id=self._vhub.id),
            connections=connections,
        )

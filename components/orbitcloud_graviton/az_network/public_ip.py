from typing import Literal, Optional

import pulumi
from pulumi_azure_native.network import v20230901 as network
from pydantic import BaseModel, ConfigDict, model_validator

from orbitcloud_graviton.pulumi_lib import AzureStack


class PublicIpDnsConfig(BaseModel):
    dns_name: str
    dns_scope: Optional[
        Literal["TENANT_REUSE", "SUBSCRIPTION_REUSE", "RESOURCE_GROUP_REUSE", "NO_REUSE"]
    ] = None


class PublicIpConfig(BaseModel):
    # resource: pulumi.CustomResource
    workload: str
    address_version: Optional[Literal["IPv4", "IPv6"]] = "IPv4"
    tier: Optional[Literal["Regional", "Global"]] = "Regional"
    idle_timeout_in_minutes: Optional[int] = 4
    zone: Optional[Literal["1", "2", "3"]] = None
    dns_config: Optional[PublicIpDnsConfig] = None

    @model_validator(mode="after")
    def validate_public_ip_config(m: "PublicIpConfig") -> "PublicIpConfig":
        if m.tier == "Global" and m.zone:
            pulumi.warn(
                "Public IP address with Global tier does not support zone selection. Ignoring zone."
            )
        return m

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class PublicIp:
    def __init__(
        self,
        stack: AzureStack,
        config: PublicIpConfig,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        self.stack: AzureStack = stack
        self.config: PublicIpConfig = config
        self._opts: pulumi.ResourceOptions = opts or pulumi.ResourceOptions()

        self.public_ip: network.PublicIPAddress = self._public_ip()

    def _dns_config(self) -> Optional[network.PublicIPAddressDnsSettingsArgs]:
        if self.config.dns_config:
            dns_scope_type = None
            if self.config.dns_config.dns_scope:
                dns_scope_map = {
                    "TENANT_REUSE": network.PublicIpAddressDnsSettingsDomainNameLabelScope.TENANT_REUSE,
                    "SUBSCRIPTION_REUSE": network.PublicIpAddressDnsSettingsDomainNameLabelScope.SUBSCRIPTION_REUSE,
                    "RESOURCE_GROUP_REUSE": network.PublicIpAddressDnsSettingsDomainNameLabelScope.RESOURCE_GROUP_REUSE,
                    "NO_REUSE": network.PublicIpAddressDnsSettingsDomainNameLabelScope.NO_REUSE,
                }
                dns_scope_type = dns_scope_map.get(self.config.dns_config.dns_scope)

            return network.PublicIPAddressDnsSettingsArgs(
                domain_name_label=self.config.dns_config.dns_name,
                domain_name_label_scope=dns_scope_type,
            )
        return None

    def _sku(self) -> network.PublicIPAddressSkuArgs:
        if self.config.tier == "Global":
            tier = network.PublicIPAddressSkuTier.GLOBAL_
        else:
            tier = network.PublicIPAddressSkuTier.REGIONAL
        return network.PublicIPAddressSkuArgs(
            name=network.PublicIPAddressSkuName.STANDARD,
            tier=tier,
        )

    def _public_ip(self) -> network.PublicIPAddress:
        public_ip_name: str = "pip-" + self.config.workload
        return network.PublicIPAddress(
            resource_name=public_ip_name,
            public_ip_address_version=self.config.address_version,
            idle_timeout_in_minutes=self.config.idle_timeout_in_minutes,
            zones=[self.config.zone] if self.config.zone and self.config.tier != "Global" else None,
            dns_settings=self._dns_config(),
            sku=self._sku(),
            location=self.stack.location,
            resource_group_name=self.stack.resource_group.name,
            public_ip_allocation_method=network.IPAllocationMethod.STATIC,
            opts=self._opts,
        )

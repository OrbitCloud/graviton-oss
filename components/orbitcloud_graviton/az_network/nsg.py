from ipaddress import IPv4Network
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from orbitcloud_graviton.az_lib.types import StrRef

from .helpers import is_service_tag


class NsgRuleConfig(BaseModel):
    name: str
    action: Literal["Allow", "Deny"] = "Allow"
    destination_addresses: StrRef | IPv4Network | str | list[IPv4Network | StrRef] = "*"
    destination_port_range: str = "*"
    source_addresses: StrRef | IPv4Network | str | list[IPv4Network | StrRef] = "*"
    source_port_range: str = "*"
    direction: Literal["Inbound", "Outbound"] = "Inbound"
    priority: int | None = None
    protocol: Literal["*", "TCP", "UDP", "ICMP"] = "TCP"
    description: str | None = None

    @model_validator(mode="after")
    def validate_addresses(m: "NsgRuleConfig") -> "NsgRuleConfig":
        # Check if Source/Destination Addresses is IP/Network, Wildcard or a valid Service Tag
        if isinstance(m.source_addresses, str):
            try:
                IPv4Network(m.source_addresses)
            except ValueError:
                if m.source_addresses == "*" or is_service_tag(m.source_addresses):
                    return m
        if isinstance(m.destination_addresses, str):
            try:
                IPv4Network(m.destination_addresses)
            except ValueError:
                if m.destination_addresses == "*" or is_service_tag(m.destination_addresses):
                    return m
        return m

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


DEFAULT_DENY_RULE = NsgRuleConfig(
    action="Deny",
    destination_addresses="*",
    destination_port_range="*",
    source_addresses="*",
    source_port_range="*",
    direction="Inbound",
    name="Deny_All_Traffic_Not_Specified_Above",
    priority=4096,
    protocol="*",
    description="Deny all inbound traffic not specified above",
)

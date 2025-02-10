from ipaddress import IPv4Address, IPv4Network
from typing import Annotated, Literal

import pulumi
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field
from pydantic.functional_serializers import PlainSerializer

from orbitcloud_graviton.pulumi_lib.types import DomainName


def is_private_network(v: str) -> IPv4Network:
    if "/" not in v:
        raise ValueError("must be in CIDR format")
    network = IPv4Network(v, strict=True)

    if not network.is_private:
        raise ValueError("must be a private network")

    return IPv4Network(v)


def is_public_network(v: str) -> IPv4Network:
    if "/" not in v:
        raise ValueError("must be in CIDR format")
    network = IPv4Network(v, strict=True)

    if network.is_private:
        raise ValueError("must be a public network")

    return IPv4Network(v)


PrivateIPv4Network = Annotated[
    IPv4Network,
    PlainSerializer(lambda x: str(x), return_type=str),
    BeforeValidator(is_private_network),
]

PublicIPv4Network = Annotated[
    IPv4Network,
    PlainSerializer(lambda x: str(x), return_type=str),
    BeforeValidator(is_public_network),
]


class PublicIpv4FirewallRule(BaseModel):
    name: str
    cidr: PublicIPv4Network

    @property
    def first_ip(self) -> str:
        return str(self.cidr[0])

    @property
    def last_ip(self) -> str:
        return str(self.cidr[-1])

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ARecord(BaseModel):
    relative_name: str = Field(..., pattern=r"^[a-zA-Z0-9-*]+(\.[a-zA-Z0-9-*]+)?$")
    ttl: int = Field(default=300, ge=60)
    record_type: Literal["A"] = "A"
    ip_addresses: list[IPv4Address] | list[pulumi.Output[str]]
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class CnameRecord(BaseModel):
    relative_name: str = Field(..., pattern=r"^[a-zA-Z0-9-*]+$")
    ttl: int = Field(default=300, ge=60)
    record_type: Literal["CNAME"] = "CNAME"
    value: DomainName
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class NsRecord(BaseModel):
    relative_name: str | pulumi.Output
    ttl: int = Field(default=300, ge=60)
    record_type: Literal["NS"] = "NS"
    ns_records: list[str] | pulumi.Output
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class MxRecord(BaseModel):
    relative_name: str = Field(..., pattern="^[a-zA-Z0-9-]+$")
    ttl: int = Field(default=300, ge=60)
    record_type: Literal["MX"] = "MX"
    preference: int
    exchange: DomainName
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class TxtRecord(BaseModel):
    relative_name: str = Field(..., pattern=r"^[a-zA-Z0-9-*]+(\.[a-zA-Z0-9-*]+)?$")
    ttl: int = Field(default=300, ge=60)
    record_type: Literal["TXT"] = "TXT"
    values: list[str | pulumi.Output[str]]
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


Record = Annotated[
    ARecord | CnameRecord | NsRecord | MxRecord | TxtRecord,
    Field(discriminator="record_type"),
]

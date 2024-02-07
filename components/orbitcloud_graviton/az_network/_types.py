from ipaddress import IPv4Network
from typing import Annotated

from pydantic import BeforeValidator
from pydantic.functional_serializers import PlainSerializer


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
    PlainSerializer(lambda x: str(x.with_netmask), return_type=str),
    BeforeValidator(is_private_network),
]

PublicIPv4Network = Annotated[
    IPv4Network,
    PlainSerializer(lambda x: str(x.with_netmask), return_type=str),
    BeforeValidator(is_public_network),
]

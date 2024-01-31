from ipaddress import IPv4Network
from typing import Annotated

from pydantic import BeforeValidator
from pydantic.functional_serializers import PlainSerializer


def ipv4network_validator(v: str) -> IPv4Network:
    if "/" not in v:
        raise ValueError("must be in CIDR format")
    network = IPv4Network(v, strict=True)

    if not network.is_private:
        raise ValueError("must be a private network")

    return IPv4Network(v)


PrivateIPv4Network = Annotated[
    IPv4Network,
    PlainSerializer(lambda x: str(x.with_netmask), return_type=str),
    BeforeValidator(ipv4network_validator),
]

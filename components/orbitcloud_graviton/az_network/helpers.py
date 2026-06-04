# helpers.py
from functools import lru_cache

from azure.core.credentials import AccessToken
from azure.mgmt.network import NetworkManagementClient
from pulumi_azure_native import authorization


class TokenCred:
    def __init__(self, token):
        self.token = token

    def get_token(self, *scopes, **kwargs) -> "AccessToken":
        return AccessToken(token=self.token, expires_on=-1)


@lru_cache
def fetch_service_tags(location: str):
    config = authorization.get_client_config()
    client_token = authorization.get_client_token()
    client = NetworkManagementClient(
        credential=TokenCred(client_token.token), subscription_id=config.subscription_id
    )
    service_tags = client.service_tags.list(location=location)

    if service_tags and service_tags.values:
        return [tag.name for tag in service_tags.values if hasattr(tag, "name")]  # type: ignore
    else:
        raise RuntimeError("Failed to fetch service tags")


# Default/system service tags represent dynamic scopes with no fixed IP
# prefixes (the VNet address space, the platform load balancer, everything
# outside the VNet). They are valid in NSG rules but are NOT returned by the
# serviceTags.list API, so they must be allowed explicitly.
DEFAULT_SERVICE_TAGS = frozenset({"VirtualNetwork", "AzureLoadBalancer", "Internet"})


def is_service_tag(value: str) -> str:
    if value in DEFAULT_SERVICE_TAGS:
        return value
    valid_service_tags = fetch_service_tags(location="northeurope")
    if value not in valid_service_tags:
        raise ValueError(f"'{value}' is not a valid service tag")
    return value


@lru_cache
def fetch_fqdn_tags():
    config = authorization.get_client_config()
    client_token = authorization.get_client_token()
    client = NetworkManagementClient(
        credential=TokenCred(client_token.token), subscription_id=config.subscription_id
    )
    fqdn_tags = client.azure_firewall_fqdn_tags.list_all()

    return [item.fqdn_tag_name for item in fqdn_tags if hasattr(item, "fqdn_tag_name")]


def is_fqdn_tag(value: str) -> str:
    valid_fqdn_tags = fetch_fqdn_tags()
    if value not in valid_fqdn_tags:
        raise ValueError(f"'{value}' is not a valid FQDN tag")
    return value


def is_port(port):
    """
    Validates a port or a range of ports.

    Args:
        port (str or int): The port or range to validate. It can be an integer,
                           a string representing a single port, a wildcard "*",
                           or a string representing a port range like "1024-2048".

    Raises:
        ValueError: If the port or port range is invalid.
    """
    if isinstance(port, int):
        if port < 1 or port > 65535:
            raise ValueError(f"Port number {port} is out of the valid range (0-65535).")
    elif isinstance(port, str):
        if port == "*":
            return
        if "-" in port:
            start, end = port.split("-")
            if not (start.isdigit() and end.isdigit()):
                raise ValueError(
                    f"Port range {port} is invalid. Both start and end must be numbers."
                )
            start, end = int(start), int(end)
            if start < 1 or end > 65535 or start > end:
                raise ValueError(
                    f"Port range {port} is out of the valid range (0-65535) or invalid."
                )
        else:
            if not port.isdigit():
                raise ValueError(f"Port {port} is invalid. It must be a number or a valid range.")
            if int(port) < 1 or int(port) > 65535:
                raise ValueError(f"Port number {port} is out of the valid range (0-65535).")
    else:
        raise ValueError(f"Invalid port format: {port}")

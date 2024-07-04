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


def is_service_tag(value: str) -> str:
    valid_service_tags = fetch_service_tags(location="northeurope")
    if value not in valid_service_tags:
        raise ValueError(f"'{value}' is not a valid service tag")
    return value

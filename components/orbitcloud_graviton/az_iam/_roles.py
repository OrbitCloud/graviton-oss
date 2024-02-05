from functools import lru_cache

from azure.core.credentials import AccessToken
from azure.mgmt.authorization import AuthorizationManagementClient
from pulumi_azure_native import authorization


class TokenCred:
    def __init__(self, token):
        self.token = token

    def get_token(self, *scopes, **kwargs) -> "AccessToken":
        return AccessToken(token=self.token, expires_on=-1)


@lru_cache
def get_role_id_by_name(name: str):
    scope = ""
    config = authorization.get_client_config()
    client_token = authorization.get_client_token()
    client = AuthorizationManagementClient(TokenCred(client_token.token), config.subscription_id)
    def_pages = client.role_definitions.list(scope, filter=f"roleName eq '{name}'")
    role = None
    for x in def_pages:
        role = x.id
        break
    if role is None:
        raise Exception(f"role '{name}' not found at scope '{scope}'")
    return role

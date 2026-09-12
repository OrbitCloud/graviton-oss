import asyncio
from collections.abc import AsyncIterable
from functools import cache

from azure.core.credentials import AccessToken
from azure.core.credentials_async import AsyncTokenCredential
from azure.mgmt.authorization.v2022_04_01.aio import AuthorizationManagementClient
from azure.mgmt.authorization.v2022_04_01.models._models_py3 import RoleDefinition
from pulumi_azure_native import authorization

from orbitcloud_graviton.az_lib.aio import async_output


class TokenCred(AsyncTokenCredential):
    def __init__(self, token) -> None:
        self.token = token

    # @in_event_loop
    async def get_token(self, *scopes, **kwargs) -> "AccessToken":
        return AccessToken(token=self.token, expires_on=-1)


async def get_roles() -> AsyncIterable[RoleDefinition]:
    client = AuthorizationManagementClient(
        credential=TokenCred(token=authorization.get_client_token().token),
        subscription_id=authorization.get_client_config().subscription_id,
        api_version="2022-05-01-preview",
    )
    return client.role_definitions.list(scope="")


@cache
def get_roles_task() -> asyncio.Task[AsyncIterable[RoleDefinition]]:
    """Start the role-definition listing once per process.

    Deliberately lazy. Creating the task at import time needs a running event
    loop, which made `import orbitcloud_graviton.az_iam` fail outside a Pulumi
    runtime -- and with it every component that wires up role assignments.
    """
    return asyncio.get_running_loop().create_task(get_roles())


@async_output
async def get_role_id_by_name(
    role_name: str, get_role_task: asyncio.Task[AsyncIterable[RoleDefinition]] | None = None
) -> str:
    async for role in await (get_role_task or get_roles_task()):
        if (
            role.role_name == role_name
            and role.id is not None
            and isinstance(role.id, str)
            and role.id != ""
        ):
            return role.id
    raise ValueError(f"Role {role_name} not found")

from typing import Annotated

from pulumi_azuread import AwaitableGetDirectoryRoleTemplatesResult, get_directory_role_templates
from pydantic import BeforeValidator

try:
    entra_roles: AwaitableGetDirectoryRoleTemplatesResult = get_directory_role_templates()
except Exception as e:
    raise ValueError(f"Error fetching Entra roles (components/entra/roles.py): {e}") from e


def get_entra_role_id_by_name(role_name: str) -> str:
    for role in entra_roles.role_templates:
        if role.display_name == role_name:
            return role.object_id
    raise ValueError(f"{role_name} role not found in the list of available Entra roles.")


EntraRole = Annotated[
    str,
    BeforeValidator(get_entra_role_id_by_name),
]

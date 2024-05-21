from typing import Annotated

from pulumi_azuread import get_directory_role_templates
from pydantic import BeforeValidator

entra_roles = get_directory_role_templates()


def get_entra_role_id_by_name(role_name: str) -> str:
    for role in entra_roles.role_templates:
        if role.display_name == role_name:
            return role.object_id
    raise ValueError(f"{role_name} role not found in the list of available Entra roles.")


EntraRole = Annotated[
    str,
    BeforeValidator(get_entra_role_id_by_name),
]

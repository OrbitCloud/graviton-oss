from functools import cache
from typing import Annotated

from pulumi_azuread import AwaitableGetDirectoryRoleTemplatesResult, get_directory_role_templates
from pydantic import BeforeValidator


@cache
def get_entra_roles() -> AwaitableGetDirectoryRoleTemplatesResult:
    """Fetch the tenant's Entra role templates, once per process.

    Deliberately lazy. Reading role templates needs directory read permission in
    the target tenant, which we do not have everywhere -- fetching this at import
    time made `import orbitcloud_graviton.entra` fail outright on those tenants,
    taking down stacks that never reference an Entra role.
    """
    try:
        return get_directory_role_templates()
    except Exception as e:
        raise ValueError(f"Error fetching Entra roles (components/entra/roles.py): {e}") from e


def get_entra_role_id_by_name(role_name: str) -> str:
    for role in get_entra_roles().role_templates:
        if role.display_name == role_name:
            return role.object_id
    raise ValueError(f"{role_name} role not found in the list of available Entra roles.")


EntraRole = Annotated[
    str,
    BeforeValidator(get_entra_role_id_by_name),
]

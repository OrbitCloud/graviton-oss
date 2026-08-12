import importlib.util
import pathlib
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

import pulumi_azuread
import pytest

# ---------------------------------------------------------------------------
# Load roles.py directly. Importing via the package would run entra/__init__,
# which pulls in entra_app.py -> az_iam, whose _roles module calls
# asyncio.get_running_loop() at import time and fails during collection. Same
# direct-load pattern used by the az_sql and az_app tests.
# ---------------------------------------------------------------------------
_ROLES_PATH = (
    pathlib.Path(__file__).resolve().parents[4]
    / "components"
    / "orbitcloud_graviton"
    / "entra"
    / "roles.py"
)


def _load_roles(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, _ROLES_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


roles = _load_roles("orbitcloud_graviton.entra._roles_under_test")

ROLE_TEMPLATES = SimpleNamespace(
    role_templates=[
        SimpleNamespace(display_name="Cloud Application Administrator", object_id="role-id-caa"),
        SimpleNamespace(display_name="Directory Readers", object_id="role-id-dr"),
    ]
)


@pytest.fixture(autouse=True)
def clear_role_cache():
    roles.get_entra_roles.cache_clear()
    yield
    roles.get_entra_roles.cache_clear()


def test_loading_the_module_does_not_hit_the_directory() -> None:
    """Tenants without directory read permission must still be able to import
    the module; a failing fetch may only surface when a role is looked up."""
    with patch.object(
        pulumi_azuread, "get_directory_role_templates", side_effect=RuntimeError("no access")
    ) as fetch:
        module = _load_roles("orbitcloud_graviton.entra._roles_import_only")
        assert fetch.call_count == 0

        with pytest.raises(ValueError, match="Error fetching Entra roles"):
            module.get_entra_roles()


def test_role_templates_are_fetched_once_per_process() -> None:
    with patch.object(roles, "get_directory_role_templates", return_value=ROLE_TEMPLATES) as fetch:
        assert roles.get_entra_role_id_by_name("Cloud Application Administrator") == "role-id-caa"
        assert roles.get_entra_role_id_by_name("Directory Readers") == "role-id-dr"

        assert fetch.call_count == 1


def test_fetch_failure_is_reported_with_context() -> None:
    with patch.object(roles, "get_directory_role_templates", side_effect=RuntimeError("no access")):
        with pytest.raises(ValueError, match="Error fetching Entra roles"):
            roles.get_entra_roles()


def test_unknown_role_name_raises() -> None:
    with patch.object(roles, "get_directory_role_templates", return_value=ROLE_TEMPLATES):
        with pytest.raises(ValueError, match="Nonexistent Role role not found"):
            roles.get_entra_role_id_by_name("Nonexistent Role")

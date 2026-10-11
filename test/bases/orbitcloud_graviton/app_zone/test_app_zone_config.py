import pathlib
import sys
import types

import pytest
from pydantic import ValidationError

from orbitcloud_graviton.pulumi_mocks import set_mocks

set_mocks()

# Stub out az_iam and az_app to avoid the asyncio.get_running_loop() call
# in _roles.py during import. We only need the Pydantic config models here.
_bases_dir = pathlib.Path(__file__).resolve().parents[4] / "bases"
_components_dir = pathlib.Path(__file__).resolve().parents[4] / "components"

# Stub az_iam so it doesn't import _roles.py
if "orbitcloud_graviton.az_iam" not in sys.modules:
    _iam_pkg = types.ModuleType("orbitcloud_graviton.az_iam")
    _iam_dir = _components_dir / "orbitcloud_graviton" / "az_iam"
    _iam_pkg.__path__ = [str(_iam_dir)]  # type: ignore[attr-defined]
    _iam_pkg.__package__ = "orbitcloud_graviton.az_iam"

    # Provide the names that container_app.py imports
    from pydantic import BaseModel  # noqa: E402

    class _StubIamAssignmentConfig(BaseModel):
        pass

    def _stub_iam_assignment(*args, **kwargs):
        """No-op replacement for iam_assignment during testing."""

    _iam_pkg.IamAssignmentConfig = _StubIamAssignmentConfig  # type: ignore[attr-defined]
    _iam_pkg.iam_assignment = _stub_iam_assignment  # type: ignore[attr-defined]
    sys.modules["orbitcloud_graviton.az_iam"] = _iam_pkg
    sys.modules["orbitcloud_graviton.az_iam.assignment"] = _iam_pkg

from orbitcloud_graviton.app_zone.app_zone_base import AppZoneBaseConfig  # noqa: E402
from orbitcloud_graviton.az_storage import StorageAccountConfig  # noqa: E402


class TestAppZoneBaseConfigStorageAccounts:
    """AppZoneBaseConfig.storage_accounts must reject duplicate name values."""

    def test_no_storage_accounts_is_valid(self) -> None:
        """None (default) is valid."""
        config = AppZoneBaseConfig()
        assert config.storage_accounts is None

    def test_single_storage_account_is_valid(self) -> None:
        """A single storage account passes validation."""
        config = AppZoneBaseConfig(storage_accounts=[StorageAccountConfig(name="alpha")])
        assert config.storage_accounts is not None
        assert len(config.storage_accounts) == 1

    def test_unique_names_are_valid(self) -> None:
        """Multiple storage accounts with unique names pass validation."""
        config = AppZoneBaseConfig(
            storage_accounts=[
                StorageAccountConfig(name="alpha"),
                StorageAccountConfig(name="beta"),
            ]
        )
        assert config.storage_accounts is not None
        assert len(config.storage_accounts) == 2

    def test_duplicate_names_rejected(self) -> None:
        """Duplicate name values in storage_accounts raise ValidationError."""
        with pytest.raises(ValidationError, match="duplicate"):
            AppZoneBaseConfig(
                storage_accounts=[
                    StorageAccountConfig(name="alpha"),
                    StorageAccountConfig(name="alpha"),
                ]
            )

    def test_empty_list_is_valid(self) -> None:
        """An empty storage_accounts list is valid."""
        config = AppZoneBaseConfig(storage_accounts=[])
        assert config.storage_accounts == []

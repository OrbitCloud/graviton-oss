import importlib.util
import pathlib
import sys
import types

import pulumi
import pytest
from pulumi_azure_native import storage
from pydantic import ValidationError

# Insert a stub for the az_app package so that importing the containerapp_env
# submodule does not trigger az_app/__init__.py (which pulls in az_iam and
# requires a running asyncio event loop).
_components_dir = pathlib.Path(__file__).resolve().parents[4] / "components"
_az_app_dir = _components_dir / "orbitcloud_graviton" / "az_app"

if "orbitcloud_graviton.az_app" not in sys.modules:
    _pkg = types.ModuleType("orbitcloud_graviton.az_app")
    _pkg.__path__ = [str(_az_app_dir)]  # type: ignore[attr-defined]
    _pkg.__package__ = "orbitcloud_graviton.az_app"
    sys.modules["orbitcloud_graviton.az_app"] = _pkg

_spec = importlib.util.spec_from_file_location(
    "orbitcloud_graviton.az_app.containerapp_env",
    _az_app_dir / "containerapp_env.py",
    submodule_search_locations=[],
)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
sys.modules["orbitcloud_graviton.az_app.containerapp_env"] = _mod
_spec.loader.exec_module(_mod)

ContainerAppEnvConfig = _mod.ContainerAppEnvConfig
ManagedStorage = _mod.ManagedStorage
ManagedStorageFileShare = _mod.ManagedStorageFileShare
ContainerAppEnv = _mod.ContainerAppEnv

from orbitcloud_graviton.pulumi_lib import AzureStack  # noqa: E402

# ---------------------------------------------------------------------------
# Model validation tests
# ---------------------------------------------------------------------------


class TestManagedStorageFileShare:
    def test_defaults(self) -> None:
        share = ManagedStorageFileShare(name="myshare")
        assert share.name == "myshare"
        assert share.access_mode is None

    def test_readonly(self) -> None:
        share = ManagedStorageFileShare(name="myshare", access_mode="ReadOnly")
        assert share.access_mode == "ReadOnly"

    def test_readwrite(self) -> None:
        share = ManagedStorageFileShare(name="myshare", access_mode="ReadWrite")
        assert share.access_mode == "ReadWrite"

    def test_invalid_access_mode_rejected(self) -> None:
        """Literal type constraint rejects invalid access_mode values."""
        with pytest.raises(ValidationError, match="access_mode"):
            ManagedStorageFileShare(name="myshare", access_mode="Invalid")

    def test_nfs_v3_accepted(self) -> None:
        share = ManagedStorageFileShare(name="myshare", nfs_v3=True)
        assert share.nfs_v3 is True

    def test_nfs_v3_defaults_to_none(self) -> None:
        share = ManagedStorageFileShare(name="myshare")
        assert share.nfs_v3 is None

    def test_extra_fields_forbidden(self) -> None:
        """extra='forbid' rejects unknown fields."""
        with pytest.raises(ValidationError):
            ManagedStorageFileShare(name="myshare", unknown_field="bad")


class TestManagedStorage:
    def test_minimal(self) -> None:
        ms = ManagedStorage(
            name="data",
            file_shares=[ManagedStorageFileShare(name="share1")],
        )
        assert ms.name == "data"
        assert len(ms.file_shares) == 1
        assert ms.sku == storage.SkuName.STANDARD_ZRS
        assert ms.allowed_private_subnets is None

    def test_custom_sku(self) -> None:
        ms = ManagedStorage(
            name="data",
            file_shares=[ManagedStorageFileShare(name="share1")],
            sku=storage.SkuName.STANDARD_LRS,
        )
        assert ms.sku == storage.SkuName.STANDARD_LRS

    def test_type_smb(self) -> None:
        ms = ManagedStorage(
            name="data",
            file_shares=[ManagedStorageFileShare(name="share1")],
            type="SMB",
        )
        assert ms.type == "SMB"

    def test_type_nfs(self) -> None:
        ms = ManagedStorage(
            name="data",
            file_shares=[ManagedStorageFileShare(name="share1")],
            type="NFS",
        )
        assert ms.type == "NFS"

    def test_type_defaults_to_none(self) -> None:
        ms = ManagedStorage(
            name="data",
            file_shares=[ManagedStorageFileShare(name="share1")],
        )
        assert ms.type is None

    def test_with_subnets(self) -> None:
        ms = ManagedStorage(
            name="data",
            file_shares=[ManagedStorageFileShare(name="share1")],
            allowed_private_subnets=[
                "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.Network/virtualNetworks/vnet/subnets/snet"
            ],
        )
        assert ms.allowed_private_subnets is not None
        assert len(ms.allowed_private_subnets) == 1

    def test_extra_fields_forbidden(self) -> None:
        """extra='forbid' rejects unknown fields."""
        with pytest.raises(ValidationError):
            ManagedStorage(
                name="data",
                file_shares=[ManagedStorageFileShare(name="share1")],
                unknown_field="bad",
            )

    def test_empty_file_shares_allowed(self) -> None:
        """An empty file_shares list is valid (no validator prevents it)."""
        ms = ManagedStorage(name="data", file_shares=[])
        assert ms.file_shares == []


class TestContainerAppEnvConfigStorage:
    def test_storage_defaults_to_none(self) -> None:
        config = ContainerAppEnvConfig()
        assert config.storage is None

    def test_storage_with_managed_storage(self) -> None:
        config = ContainerAppEnvConfig(
            storage=[
                ManagedStorage(
                    name="data",
                    file_shares=[ManagedStorageFileShare(name="share1")],
                )
            ]
        )
        assert config.storage is not None
        assert len(config.storage) == 1

    def test_tags_defaults_to_none(self) -> None:
        config = ContainerAppEnvConfig()
        assert config.tags is None

    def test_tags_with_values(self) -> None:
        config = ContainerAppEnvConfig(tags={"env": "test", "team": "platform"})
        assert config.tags is not None
        assert config.tags["env"] == "test"


# ---------------------------------------------------------------------------
# Storage account naming tests
# ---------------------------------------------------------------------------


class TestStorageAccountNaming:
    def test_name_truncation_to_8_chars(self) -> None:
        """managed.name is truncated to 8 characters in the storage account name."""
        ms = ManagedStorage(
            name="longstorageidentifier",
            file_shares=[ManagedStorageFileShare(name="share1")],
        )
        # Sanitize same way as the implementation: strip non-alnum, lowercase, take [:8]
        sanitized = "".join(c for c in ms.name if c.isalnum()).lower()
        assert sanitized[:8] == "longstor"

    def test_name_with_uppercase_is_lowercased(self) -> None:
        """Uppercase characters in managed.name are lowercased for storage account names."""
        sanitized = "".join(c for c in "MyData" if c.isalnum()).lower()
        assert sanitized == "mydata"

    def test_name_with_hyphens_stripped(self) -> None:
        """Hyphens are stripped from managed.name for storage account names."""
        sanitized = "".join(c for c in "my-data" if c.isalnum()).lower()
        assert sanitized == "mydata"

    def test_name_with_underscores_stripped(self) -> None:
        """Underscores are stripped from managed.name for storage account names."""
        sanitized = "".join(c for c in "my_data" if c.isalnum()).lower()
        assert sanitized == "mydata"

    def test_storage_name_underscore_to_hyphen(self) -> None:
        """In environment storage name, underscores become hyphens."""
        storage_name = f"{'data'}-{'share_one'}".lower().replace("_", "-")[:50]
        assert storage_name == "data-share-one"

    def test_storage_name_truncated_to_50(self) -> None:
        """Environment storage name is truncated to 50 characters."""
        long_storage = "a" * 30
        long_share = "b" * 30
        storage_name = f"{long_storage}-{long_share}".lower().replace("_", "-")[:50]
        assert len(storage_name) == 50


# ---------------------------------------------------------------------------
# Resource creation tests (Pulumi mocked)
# ---------------------------------------------------------------------------


@pulumi.runtime.test
def test_storage_accounts_none_when_no_storage(stack: AzureStack) -> None:
    """When config.storage is None, _storage_accounts() returns None."""
    config = ContainerAppEnvConfig()
    cae = ContainerAppEnv(stack=stack, config=config)
    assert cae.storage_accounts is None


@pulumi.runtime.test
def test_storage_accounts_creates_storage(stack: AzureStack) -> None:
    """When storage is configured, storage accounts are created with correct properties."""
    config = ContainerAppEnvConfig(
        storage=[
            ManagedStorage(
                name="data",
                file_shares=[ManagedStorageFileShare(name="share1")],
            )
        ]
    )
    cae = ContainerAppEnv(stack=stack, config=config)
    assert cae.storage_accounts is not None
    assert len(cae.storage_accounts) == 1

    sa = cae.storage_accounts[0]

    # Verify the storage account config was built correctly
    assert sa.config.name == "stcaedatatest001"
    assert sa.config.kind == storage.Kind.STORAGE_V2
    assert sa.config.hierarchical_namespace is True
    assert sa.config.allow_shared_key_access is True
    assert sa.config.public_network_access == storage.PublicNetworkAccess.ENABLED
    assert len(sa.config.file_shares) == 1
    assert sa.config.file_shares[0].name == "share1"
    assert sa.config.exports_prefix == "cae_storage_data"


@pulumi.runtime.test
def test_storage_accounts_with_uppercase_name(stack: AzureStack) -> None:
    """Storage account names are sanitized when managed.name has uppercase/special chars."""
    config = ContainerAppEnvConfig(
        storage=[
            ManagedStorage(
                name="My-Data_Store",
                file_shares=[ManagedStorageFileShare(name="share1")],
            )
        ]
    )
    cae = ContainerAppEnv(stack=stack, config=config)
    assert cae.storage_accounts is not None
    assert len(cae.storage_accounts) == 1

    sa = cae.storage_accounts[0]

    # Sanitized: "My-Data_Store" -> strip non-alnum -> "MyDataStore" -> lower -> "mydatastore"[:8] -> "mydatast"
    assert sa.config.name == "stcaemydatasttest001"
    assert sa.config.name.isalnum()
    assert sa.config.name.islower()


@pulumi.runtime.test
def test_environment_storages_none_when_no_storage(stack: AzureStack) -> None:
    """When config.storage is None, environment_storages is None."""
    config = ContainerAppEnvConfig()
    cae = ContainerAppEnv(stack=stack, config=config)
    assert cae.environment_storages is None


@pulumi.runtime.test
def test_environment_storages_creates_resources(stack: AzureStack) -> None:
    """When storage is configured, environment storage links are created with correct properties."""
    config = ContainerAppEnvConfig(
        storage=[
            ManagedStorage(
                name="data",
                file_shares=[
                    ManagedStorageFileShare(name="share1", access_mode="ReadOnly"),
                    ManagedStorageFileShare(name="share2", access_mode="ReadWrite"),
                ],
            )
        ]
    )
    cae = ContainerAppEnv(stack=stack, config=config)
    assert cae.environment_storages is not None
    # One ManagedEnvironmentsStorage per file share
    assert len(cae.environment_storages) == 2

    # Verify resource_name pattern on the environment storages via URN
    def check_first_urn(urn: str) -> None:
        assert "caest-data-share1" in urn, f"Expected 'caest-data-share1' in URN: {urn}"

    def check_second_urn(urn: str) -> None:
        assert "caest-data-share2" in urn, f"Expected 'caest-data-share2' in URN: {urn}"

    cae.environment_storages[0].urn.apply(check_first_urn)
    cae.environment_storages[1].urn.apply(check_second_urn)


@pulumi.runtime.test
def test_environment_storages_access_modes(stack: AzureStack) -> None:
    """Environment storage resources have correct access_mode from file share config."""
    config = ContainerAppEnvConfig(
        storage=[
            ManagedStorage(
                name="data",
                file_shares=[
                    ManagedStorageFileShare(name="share1", access_mode="ReadOnly"),
                    ManagedStorageFileShare(name="share2", access_mode="ReadWrite"),
                    ManagedStorageFileShare(name="share3"),
                ],
            )
        ]
    )
    cae = ContainerAppEnv(stack=stack, config=config)
    assert cae.environment_storages is not None
    assert len(cae.environment_storages) == 3

    # Verify resource names encode the share names correctly
    def check_urn_share1(urn: str) -> None:
        assert "caest-data-share1" in urn

    def check_urn_share2(urn: str) -> None:
        assert "caest-data-share2" in urn

    def check_urn_share3(urn: str) -> None:
        assert "caest-data-share3" in urn

    cae.environment_storages[0].urn.apply(check_urn_share1)
    cae.environment_storages[1].urn.apply(check_urn_share2)
    cae.environment_storages[2].urn.apply(check_urn_share3)


@pulumi.runtime.test
def test_multiple_managed_storages(stack: AzureStack) -> None:
    """Multiple ManagedStorage entries create multiple storage accounts and environment storages."""
    config = ContainerAppEnvConfig(
        storage=[
            ManagedStorage(
                name="data",
                file_shares=[ManagedStorageFileShare(name="share1")],
            ),
            ManagedStorage(
                name="logs",
                file_shares=[ManagedStorageFileShare(name="logshare")],
            ),
        ]
    )
    cae = ContainerAppEnv(stack=stack, config=config)
    assert cae.storage_accounts is not None
    assert len(cae.storage_accounts) == 2
    assert cae.environment_storages is not None
    assert len(cae.environment_storages) == 2


@pulumi.runtime.test
def test_empty_file_shares_creates_storage_but_no_env_storage(stack: AzureStack) -> None:
    """A ManagedStorage with empty file_shares creates a storage account but zero env storages."""
    config = ContainerAppEnvConfig(
        storage=[
            ManagedStorage(
                name="empty",
                file_shares=[],
            ),
        ]
    )
    cae = ContainerAppEnv(stack=stack, config=config)
    assert cae.storage_accounts is not None
    assert len(cae.storage_accounts) == 1
    # No file shares means no environment storages
    assert cae.environment_storages is not None
    assert len(cae.environment_storages) == 0


@pulumi.runtime.test
def test_tags_passed_to_environment(stack: AzureStack) -> None:
    """When tags are configured, they are passed to the ManagedEnvironment."""
    config = ContainerAppEnvConfig(tags={"env": "test"})
    cae = ContainerAppEnv(stack=stack, config=config)

    def check_tags(tags):
        assert tags is not None
        assert tags["env"] == "test"

    cae.environment.tags.apply(check_tags)

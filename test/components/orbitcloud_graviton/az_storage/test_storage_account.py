from unittest.mock import patch

import pulumi
import pytest
from pulumi_azure_native import storage
from pydantic import ValidationError

from orbitcloud_graviton.pulumi_mocks import set_mocks

set_mocks()

from orbitcloud_graviton.az_storage import StorageAccount, StorageAccountConfig  # noqa: E402
from orbitcloud_graviton.az_storage.storage_account import StorageAccountRoutingConfig  # noqa: E402
from orbitcloud_graviton.pulumi_lib import AzureStack  # noqa: E402


def _minimal_config(name: str) -> StorageAccountConfig:
    """Create a minimal StorageAccountConfig that works under Pulumi mocks.

    Uses internet routing to avoid the microsoft_endpoints code path.
    """
    return StorageAccountConfig(
        name=name,
        routing=StorageAccountRoutingConfig(
            routing_preference=storage.RoutingChoice.INTERNET_ROUTING,
            publish_microsoft_endpoints=False,
            publish_internet_endpoints=False,
        ),
    )


# ---------------------------------------------------------------------------
# Config validation tests
# ---------------------------------------------------------------------------


class TestStorageAccountConfigName:
    """StorageAccountConfig.name must be a required str field."""

    def test_name_is_required(self) -> None:
        """Omitting name raises ValidationError."""
        with pytest.raises(ValidationError, match="name"):
            StorageAccountConfig()  # type: ignore[call-arg]

    def test_name_provided(self) -> None:
        """Providing a name succeeds."""
        config = StorageAccountConfig(name="mystorage")
        assert config.name == "mystorage"

    def test_name_cannot_be_none(self) -> None:
        """Explicitly passing None for name raises ValidationError."""
        with pytest.raises(ValidationError, match="name"):
            StorageAccountConfig(name=None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Pulumi resource naming tests
# ---------------------------------------------------------------------------


class TestStorageAccountResourceNaming:
    """Each StorageAccount must get a unique Pulumi ComponentResource name based on config.name."""

    @pulumi.runtime.test
    def test_resource_name_includes_config_name(self, stack: AzureStack) -> None:
        """The ComponentResource name contains config.name, not just workload_name."""
        config = _minimal_config("alpha")
        # Patch _outputs to skip endpoint/export logic that fails under mocks
        with patch.object(StorageAccount, "_outputs"):
            sa = StorageAccount(stack=stack, config=config)

        def check_urn(urn: str) -> None:
            assert "st-alpha" in urn, f"Expected 'st-alpha' in URN: {urn}"

        sa.urn.apply(check_urn)

    @pulumi.runtime.test
    def test_two_accounts_get_different_resource_names(self, stack: AzureStack) -> None:
        """Two storage accounts with different config.name get different ComponentResource names."""
        with patch.object(StorageAccount, "_outputs"):
            sa1 = StorageAccount(stack=stack, config=_minimal_config("alpha"))
            sa2 = StorageAccount(stack=stack, config=_minimal_config("beta"))

        def check_urns(args: list[str]) -> None:
            urn1, urn2 = args
            assert urn1 != urn2, "Two storage accounts should have different URNs"
            assert "st-alpha" in urn1
            assert "st-beta" in urn2

        pulumi.Output.all(sa1.urn, sa2.urn).apply(check_urns)

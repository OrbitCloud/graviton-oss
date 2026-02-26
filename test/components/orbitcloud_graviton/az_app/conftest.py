from typing import Any

import pulumi
import pytest


class StorageMocks(pulumi.runtime.Mocks):
    """Mocks that provide storage account properties required by StorageAccount._outputs()."""

    def new_resource(self, args: pulumi.runtime.MockResourceArgs) -> list[Any]:
        inputs = dict(args.inputs)
        # StorageAccount resource needs primary_endpoints populated
        if args.typ == "azure-native:storage:StorageAccount":
            inputs["primaryEndpoints"] = {
                "blob": "https://mock.blob.core.windows.net/",
                "file": "https://mock.file.core.windows.net/",
                "queue": "https://mock.queue.core.windows.net/",
                "table": "https://mock.table.core.windows.net/",
                "microsoftEndpoints": {
                    "blob": "https://mock.blob.core.windows.net/",
                    "file": "https://mock.file.core.windows.net/",
                    "queue": "https://mock.queue.core.windows.net/",
                    "table": "https://mock.table.core.windows.net/",
                },
            }
        # ManagedEnvironment needs custom_domain_configuration for _outputs()
        if args.typ == "azure-native:app:ManagedEnvironment":
            inputs.setdefault(
                "customDomainConfiguration",
                {
                    "customDomainVerificationId": "mock-verification-id",
                    "dnsSuffix": "mock-dns-suffix",
                },
            )
        return [args.name + "_id", inputs]

    def call(self, args: pulumi.runtime.MockCallArgs) -> dict[Any, Any]:
        if args.token == "azure-native:storage:listStorageAccountKeys":
            return {
                "keys": [
                    {"keyName": "key1", "value": "mock-key-value", "permissions": "Full"},
                ],
            }
        return {}


_STORAGE_MOCKS = StorageMocks()

# Set mocks at module level for module-level imports during collection
pulumi.runtime.set_mocks(
    _STORAGE_MOCKS, project="mock-project", preview=False, organization="mock-org"
)


@pytest.fixture(autouse=True)
def _set_storage_mocks() -> None:
    """Re-set storage-aware mocks before each test to guard against other test
    modules overriding the global Pulumi mock instance."""
    pulumi.runtime.set_mocks(
        _STORAGE_MOCKS, project="mock-project", preview=False, organization="mock-org"
    )

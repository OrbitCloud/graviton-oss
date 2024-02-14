import pytest
from pulumi_azure_native import (
    containerregistry,
    keyvault,
    operationalinsights,
    resources,
    storage,
)
from pulumi_azure_native.app.v20230502preview import ContainerApp as VersionedContainerApp
from pulumi_azure_native.resources.v20220901 import ResourceGroup as VersionedResourceGroup

from orbitcloud_graviton.az_lib import get_prefix, location_abbr, resource_namer


def test_resource_prefix() -> None:
    assert get_prefix(resources.ResourceGroup).get("prefix") == "rg"
    assert get_prefix(operationalinsights.Workspace).get("prefix") == "log"
    assert get_prefix(containerregistry.Registry).get("prefix") == "cr"


def test_versioned_resource_prefix() -> None:
    assert get_prefix(VersionedResourceGroup).get("prefix") == "rg"


def test_versioned_preview_prefix() -> None:
    assert get_prefix(VersionedContainerApp).get("prefix") == "app"


def test_resource_prefix_undefined() -> None:
    with pytest.raises(ValueError):
        get_prefix(object)


def test_location_abbr() -> None:
    assert location_abbr("westeurope") == "weu"
    assert location_abbr("northeurope") == "neu"
    assert location_abbr("norwayeast") == "noe"
    assert location_abbr("norwaywest") == "now"


def test_location_abbr_undefined() -> None:
    with pytest.raises(ValueError):
        location_abbr("not_a_location")


def test_resource_names() -> None:
    assert (
        resource_namer(resources.ResourceGroup, "test", "dev", "westeurope") == "rg-test-dev-weu-01"
    )
    assert (
        resource_namer(resources.ResourceGroup, "test", "dev", "swedencentral", "02")
        == "rg-test-dev-sec-02"
    )
    assert (
        resource_namer(operationalinsights.Workspace, "test", "dev", "northeurope")
        == "log-test-dev-neu-01"
    )


def test_alphanumeric_resource_names() -> None:
    assert (
        resource_namer(containerregistry.Registry, "test", "dev", "westeurope") == "CrTestDevWeu01"
    )
    assert resource_namer(keyvault.Vault, "test", "dev", "westeurope") == "KvTestDevWeu01"


def test_alphanumeric_lowercase_resource_names() -> None:
    assert get_prefix(storage.StorageAccount).get("alphanumeric") is True
    assert get_prefix(storage.StorageAccount).get("lowercase") is True
    assert resource_namer(storage.StorageAccount, "test", "dev", "westeurope") == "sttestdevweu01"


def test_resource_namer_undefined() -> None:
    with pytest.raises(ValueError):
        resource_namer(object, "test", "dev", "westeurope")

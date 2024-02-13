import pytest
from pulumi_azure_native import (
    containerregistry,
    keyvault,
    operationalinsights,
    resources,
    storage,
)

from orbitcloud_graviton.az_lib import get_prefix, location_abbr, resource_namer


def test_resource_opts() -> None:
    assert get_prefix(resources.ResourceGroup).get("prefix") == "rg"
    assert get_prefix(operationalinsights.Workspace).get("prefix") == "log"
    assert get_prefix(containerregistry.Registry).get("prefix") == "cr"
    assert get_prefix(containerregistry.Registry).get("alphanumeric")
    # assert a value error is raised when the resource type is not found
    with pytest.raises(ValueError):
        get_prefix(object)


def test_location_abbr() -> None:
    assert location_abbr("westeurope") == "weu"
    assert location_abbr("northeurope") == "neu"
    assert location_abbr("norwayeast") == "noe"
    assert location_abbr("norwaywest") == "now"

    with pytest.raises(ValueError):
        location_abbr("not_a_location")


def test_resource_namer() -> None:
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

    assert (
        resource_namer(containerregistry.Registry, "test", "dev", "westeurope") == "CrTestDevWeu01"
    )
    assert resource_namer(storage.StorageAccount, "test", "dev", "westeurope") == "sttestdevweu01"
    assert resource_namer(keyvault.Vault, "test", "dev", "westeurope") == "KvTestDevWeu01"

    # assert a value error is raised when the resource type is not found
    with pytest.raises(ValueError):
        resource_namer(object, "test", "dev", "westeurope")

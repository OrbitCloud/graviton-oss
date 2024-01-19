import pytest
from orbitcloud_graviton.az_lib import location_abbr, resource_namer, resource_opts
from pulumi_azure_native import (
    containerregistry,
    network,
    operationalinsights,
    resources,
    storage
)


def test_resource_opts() -> None:
    assert resource_opts(resources.ResourceGroup).get("prefix") == "rg"
    assert resource_opts(operationalinsights.Workspace).get("prefix") == "log"
    assert resource_opts(containerregistry.Registry).get("prefix") == "cr"
    assert resource_opts(containerregistry.Registry).get("alphanumeric")
    # assert a value error is raised when the resource type is not found
    with pytest.raises(ValueError):
        resource_opts(object)


def test_location_abbr() -> None:
    assert location_abbr("westeurope") == "weu"
    assert location_abbr("northeurope") == "neu"
    assert location_abbr("norwayeast") == "noe"
    assert location_abbr("norwaywest") == "now"

    with pytest.raises(ValueError):
        location_abbr("not_a_location")


def test_resource_namer() -> None:
    assert (
        resource_namer(resources.ResourceGroup, "test", "dev", "westeurope")
        == "rg-test-dev-weu-01"
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
        resource_namer(containerregistry.Registry, "test", "dev", "westeurope")
        == "CrTestDevWeu01"
    )
    assert (
        resource_namer(storage.StorageAccount, "test", "dev", "westeurope")
        == "sttestdevweu01"
    )

    # assert a value error is raised when the resource type is not found
    with pytest.raises(ValueError):
        resource_namer(object, "test", "dev", "westeurope")

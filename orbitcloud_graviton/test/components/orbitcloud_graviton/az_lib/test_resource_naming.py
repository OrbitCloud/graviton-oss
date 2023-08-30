import pytest
from pulumi_azure_native import operationalinsights, resources

from orbitcloud_graviton.az_lib import location_abbr, resource_namer, resource_prefix


def test_resource_prefixer():
    assert resource_prefix(resources.ResourceGroup) == "rg"
    assert resource_prefix(operationalinsights.Workspace) == "log"
    # assert a value error is raised when the resource type is not found
    with pytest.raises(ValueError):
        resource_prefix(object)


def test_location_abbr():
    assert location_abbr("westeurope") == "weu"
    assert location_abbr("northeurope") == "neu"
    assert location_abbr("norwayeast") == "noe"
    assert location_abbr("norwaywest") == "now"

    with pytest.raises(ValueError):
        location_abbr("not_a_location")


def test_resource_namer():
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

    # assert a value error is raised when the resource type is not found
    with pytest.raises(ValueError):
        resource_namer(object, "test", "dev", "westeurope")

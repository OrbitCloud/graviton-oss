import pytest
from pulumi_azure_native import containerregistry, keyvault, resources, storage
from pulumi_azure_native.resources.v20220901 import ResourceGroup as VersionedResourceGroup

from orbitcloud_graviton.az_lib.helpers import location_abbr
from orbitcloud_graviton.az_lib.meta import resource_meta
from orbitcloud_graviton.pulumi_lib import AzureStack


def test_location_abbr() -> None:
    assert location_abbr("westeurope") == "weu"
    assert location_abbr("northeurope") == "neu"
    assert location_abbr("norwayeast") == "noe"
    assert location_abbr("norwaywest") == "now"


def test_location_abbr_undefined() -> None:
    with pytest.raises(ValueError):
        location_abbr("not_a_location")


def test_resource_names(stack: AzureStack) -> None:
    assert resource_meta(resources.ResourceGroup).autoname(stack=stack) == "rg-workload-test-neu-01"


def test_versioned_resource_names(stack: AzureStack) -> None:
    assert resource_meta(VersionedResourceGroup).autoname(stack) == "rg-workload-test-neu-01"


def test_alphanumeric_resource_names(stack: AzureStack) -> None:
    assert resource_meta(containerregistry.Registry).autoname(stack) == "CrWorkloadTestNeu01"
    assert resource_meta(keyvault.Vault).autoname(stack) == "KvWorkloadTestNeu01"


def test_alphanumeric_lowercase_resource_names(stack: AzureStack) -> None:
    assert resource_meta(storage.StorageAccount).autoname(stack) == "stworkloadtestneu01"


def test_resource_name_instance_number_none(stack: AzureStack) -> None:
    assert (
        resource_meta(storage.StorageAccount).autoname(stack, instance_number=None)
        == "stworkloadtestneu"
    )


def test_resource_name_without_instance_number_empty(stack: AzureStack) -> None:
    assert (
        resource_meta(storage.StorageAccount).autoname(stack, instance_number="")
        == "stworkloadtestneu"
    )

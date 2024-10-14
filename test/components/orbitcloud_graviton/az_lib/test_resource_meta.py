import pytest
from pulumi_azure_native import containerregistry, keyvault, resources, storage
from pulumi_azure_native.resources.v20220901 import ResourceGroup as VersionedResourceGroup

from orbitcloud_graviton.az_lib.helpers import (
    fmt_name,
    location_abbr,
)
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


def test_resource_meta_basic(_: AzureStack) -> None:
    rg_meta = resource_meta(resources.ResourceGroup)
    assert rg_meta.namespace == "Microsoft.Resources/resourceGroups"
    assert rg_meta.resource_type == "resourceGroup"
    assert rg_meta.naming.prefix == "rg"
    assert rg_meta.public_dns_zone is None


def test_versioned_resource_names(_: AzureStack) -> None:
    rg_meta = resource_meta(VersionedResourceGroup)
    assert rg_meta.namespace == "Microsoft.Resources/resourceGroups"
    assert rg_meta.resource_type == "resourceGroup"
    assert rg_meta.naming.prefix == "rg"


def test_fmt_name_title_no_sep() -> None:
    assert fmt_name("rg-workload-test-neu-01", sep="", case="title") == "RgWorkloadTestNeu01"


def test_fmt_name_title() -> None:
    assert fmt_name("rg-workload-test-neu-01") == "rg-workload-test-neu-01"


def test_alphanumeric_resource_names(stack: AzureStack) -> None:
    assert resource_meta(containerregistry.Registry).autoname(stack) == "CrWorkloadTestNeu01"
    assert resource_meta(keyvault.Vault).autoname(stack) == "KvWorkloadTestNeu01"


def test_alphanumeric_lowercase_resource_names(stack: AzureStack) -> None:
    assert resource_meta(storage.StorageAccount).autoname(stack) == "stworkloadtestneu01"


def test_resource_meta_notfound() -> None:
    with pytest.raises(IndexError):
        resource_meta(object)

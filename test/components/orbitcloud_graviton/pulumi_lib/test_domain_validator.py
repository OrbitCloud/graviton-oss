import pytest

from orbitcloud_graviton.pulumi_lib.types import domain_validator


def test_domain_validator():
    assert domain_validator("orbit.is") == "orbit.is"
    assert domain_validator("example.com") == "example.com"
    assert domain_validator("subdomain.example.com") == "subdomain.example.com"
    assert domain_validator("sub-domain.example.co.uk") == "sub-domain.example.co.uk"

    with pytest.raises(ValueError):
        domain_validator("invalid_domain")

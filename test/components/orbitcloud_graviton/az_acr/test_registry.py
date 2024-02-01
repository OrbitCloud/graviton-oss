from orbitcloud_graviton.az_acr import container_registry


def test_containerregistry_exists():
    assert container_registry is not None

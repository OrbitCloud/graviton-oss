from orbitcloud_graviton.az_acr import az_containerregistry


def test_containerregistry_exists():
    assert az_containerregistry is not None

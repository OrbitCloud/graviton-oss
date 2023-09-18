from orbitcloud_graviton.az_keyvault import az_keyvault


def test_az_keyvault_exists():
    assert az_keyvault is not None

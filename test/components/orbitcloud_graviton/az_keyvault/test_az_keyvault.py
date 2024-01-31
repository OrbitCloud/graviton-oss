from orbitcloud_graviton.az_keyvault import keyvault


def test_az_keyvault_exists():
    assert keyvault is not None

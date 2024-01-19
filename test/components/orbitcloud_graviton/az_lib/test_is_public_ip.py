from orbitcloud_graviton.az_lib import is_public_ip


def test_is_public_ip() -> None:
    assert not is_public_ip("10.0.0.1")
    assert not is_public_ip("10.255.255.255")
    assert not is_public_ip("192.168.0.1")
    assert not is_public_ip("192.168.255.255")
    assert not is_public_ip("172.16.0.0")
    assert not is_public_ip("172.31.255.255")
    assert not is_public_ip("10.10.0.0/16")
    assert is_public_ip("194.100.20.30")
    assert is_public_ip("1.1.1.1/8")

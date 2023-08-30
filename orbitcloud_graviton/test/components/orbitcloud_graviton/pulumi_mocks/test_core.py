from orbitcloud_graviton.pulumi_mocks import set_mocks


def test_pulumi_mocks():
    assert set_mocks is not None

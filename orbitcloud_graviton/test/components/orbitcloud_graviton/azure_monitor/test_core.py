from orbitcloud_graviton.azure_monitor import loganalytics_workspace


def test_sample():
    assert loganalytics_workspace is not None

from orbitcloud_graviton.pulumi_mocks import set_mocks

set_mocks(
    {
        "azure-native:location": "northeurope",
        "mock-project:workload_name": "mock",
        "mock-project:env": "dev",
    },
)

# pylint: disable=wrong-import-position
from orbitcloud_graviton.loganalytics import loganalytics_base


def test_existance():
    assert loganalytics_base is not None

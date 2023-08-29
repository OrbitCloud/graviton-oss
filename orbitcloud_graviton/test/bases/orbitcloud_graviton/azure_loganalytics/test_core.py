from orbitcloud_graviton.pulumi_mocks.core import set_mocks

set_mocks(
    {
        "azure-native:location": "northeurope",
        "mock-project:workload_name": "mock",
        "mock-project:env": "dev",
    },
)

# pylint: disable=wrong-import-position
from orbitcloud_graviton.azure_loganalytics import core


def test_existance():
    assert core is not None

import json

import pulumi
import pytest

from orbitcloud_graviton.pulumi_lib import PulumiConfig
from orbitcloud_graviton.pulumi_mocks import set_mocks


@pytest.fixture(scope="module")
def pulumi_project_mock() -> None:
    set_mocks(
        {
            "azure-native:location": "northeurope",
            "mock-project:workload_name": "test-workload",
            "mock-project:env": "dev",
            "mock-project:some_other_string": "some_other_value",
            "mock-project:some_other_int": 5,
            "mock-project:some_false_bool": "false",
            "mock-project:some_true_bool": "true",
            "mock-project:some_optional_false_bool": "false",
            "mock-project:some_optional_true_bool_set_false": "false",
            "mock-project:some_optional_true_bool": "true",
            "mock-project:tags": json.dumps({"test-tag": "test-value"}),
        }
    )


@pulumi.runtime.test
@pytest.mark.usefixtures("pulumi_project_mock")
def test_pulumi_config() -> None:
    class TestBaseConfig(PulumiConfig):
        resource_group_name: str | None = "test-resource-group"
        some_other_string: str
        some_other_int: int = 1
        some_other_optional_int: int | None = 1
        some_false_bool: bool = False
        some_true_bool: bool = True
        some_optional_false_bool: bool | None = False
        some_optional_true_bool: bool | None = True
        some_optional_unset_bool: bool | None = None
        some_optional_true_bool_set_false: bool | None = True

    stack_config: TestBaseConfig = TestBaseConfig.model_validate({})

    assert stack_config.resource_group_name == "test-resource-group"
    assert stack_config.some_other_string == "some_other_value"
    assert stack_config.some_other_optional_int == 1

    assert stack_config.some_false_bool is False
    assert stack_config.some_true_bool is True
    assert stack_config.some_optional_false_bool is False
    assert stack_config.some_optional_true_bool is True
    assert stack_config.some_optional_unset_bool is None

    assert stack_config.some_optional_true_bool_set_false is False

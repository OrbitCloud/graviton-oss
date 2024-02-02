import json
from dataclasses import Field, dataclass, field, fields
from typing import Annotated, Any, Collection, Optional

import pulumi
import pytest

from orbitcloud_graviton.az_lib import Confy, StackConfig
from orbitcloud_graviton.pulumi_mocks import set_mocks


@pytest.fixture(scope="module")
def pulumi_project_mock():
    set_mocks(
        {
            "azure-native:location": "northeurope",
            "mock-project:workload_name": "test-workload",
            "mock-project:env": "dev",
            "mock-project:some_other_string": "some_other_value",
            "mock-project:some_other_int": 5,
            "mock-project:tags": json.dumps({"test-tag": "test-value"}),
        }
    )


@dataclass(kw_only=True)
class DummyDataclass:
    string_field: str
    string_field_with_default: str = "default"
    string_field_optional: Optional[str] = None
    string_field_optional_with_default: Optional[str] = "default"
    int_field: int
    int_field_with_default: int = 1
    int_field_optional: Optional[int] = None
    int_field_optional_with_default: Optional[int] = 1
    bool_field: bool
    bool_field_with_default: bool = True
    bool_field_optional: Optional[bool] = None
    bool_field_optional_with_default: Optional[bool] = True
    dict_field: dict
    dict_field_with_default: dict = field(default_factory=lambda: {})
    dict_field_optional: Optional[dict] = None
    dict_field_optional_with_default: Optional[dict] = field(default_factory=lambda: {})
    list_field: list
    list_field_with_default: list = field(default_factory=lambda: [])
    list_field_optional: Optional[list] = None
    list_field_optional_with_default: Optional[list] = field(default_factory=lambda: [])
    tuple_field: tuple
    tuple_field_with_default: tuple = field(default_factory=lambda: ())
    tuple_field_optional: Optional[tuple] = None
    tuple_field_optional_with_default: Optional[tuple] = field(default_factory=lambda: ())
    secret_str_field: Annotated[str, "secret"]
    secret_str_field_with_default: Annotated[str, "secret"] = "default"
    secret_str_field_optional: Optional[Annotated[str, "secret"]] = None
    secret_str_field_optional_with_default: Optional[Annotated[str, "secret"]] = "default"
    secret_int_field: Annotated[int, "secret"]
    secret_int_field_with_default: Annotated[int, "secret"] = 1
    secret_int_field_optional: Optional[Annotated[int, "secret"]] = None
    secret_int_field_optional_with_default: Optional[Annotated[int, "secret"]] = 1
    secret_bool_field: Annotated[bool, "secret"]
    secret_bool_field_with_default: Annotated[bool, "secret"] = True
    secret_bool_field_optional: Optional[Annotated[bool, "secret"]] = None
    secret_bool_field_optional_with_default: Optional[Annotated[bool, "secret"]] = True
    secret_dict_field: Annotated[dict, "secret"]
    secret_dict_field_with_default: Annotated[dict, "secret"] = field(default_factory=lambda: {})
    secret_dict_field_optional: Optional[Annotated[dict, "secret"]] = None
    secret_dict_field_optional_with_default: Optional[Annotated[dict, "secret"]] = field(
        default_factory=lambda: {}
    )
    azure_native_str_field: Annotated[str, "azure-native"]
    azure_native_str_field_with_default: Annotated[str, "azure-native"] = "default"
    azure_native_str_field_optional: Optional[Annotated[str, "azure-native"]] = None
    azure_native_str_field_optional_with_default: Optional[
        Annotated[str, "azure-native"]
    ] = "default"


@pytest.fixture(scope="module")
def config_fields() -> dict[str, Field[Any]]:
    dcfields_dict: dict[str, Field[Any]] = {
        dcfield.name: dcfield for dcfield in fields(DummyDataclass)
    }
    return dcfields_dict


@pulumi.runtime.test
@pytest.mark.usefixtures("pulumi_project_mock")
def test_confy_stack() -> None:
    @dataclass(kw_only=True, frozen=True)
    class TestBaseConfig(StackConfig):
        resource_group_name: Optional[str] = "test-resource-group"
        some_other_string: str
        some_other_int: int = 1
        some_other_optional_int: Optional[int] = 1

    stack_config: TestBaseConfig = Confy(dataclass_obj=TestBaseConfig).populate()

    assert stack_config.workload_name == "test-workload"
    assert stack_config.env == "dev"
    # assert stack_config.tags == {"test-tag": "test-value"}
    assert stack_config.resource_group_name == "test-resource-group"
    assert stack_config.some_other_string == "some_other_value"
    assert stack_config.some_other_optional_int == 1


@pytest.mark.usefixtures("config_fields")
def test_config_getter_func_strings(request) -> None:
    dcfields = request.getfixturevalue("config_fields")
    config = pulumi.Config()

    for field_name, config_func in [
        ("string_field", config.require),
        ("string_field_with_default", config.require),
        ("string_field_optional", config.get),
        ("string_field_optional_with_default", config.get),
    ]:
        assert Confy.config_getter_func(dcfield=dcfields[field_name], config=config) == config_func


@pytest.mark.usefixtures("config_fields")
def test_config_getter_func_ints(request) -> None:
    dcfields = request.getfixturevalue("config_fields")
    config = pulumi.Config()
    for field_name, config_func in [
        ("int_field", config.require_int),
        ("int_field_with_default", config.require_int),
        ("int_field_optional", config.get_int),
        ("int_field_optional_with_default", config.get_int),
    ]:
        assert Confy.config_getter_func(dcfield=dcfields[field_name], config=config) == config_func


@pytest.mark.usefixtures("config_fields")
def test_config_getter_func_bools(request) -> None:
    dcfields = request.getfixturevalue("config_fields")
    config = pulumi.Config()
    for field_name, config_func in [
        ("bool_field", config.require_bool),
        ("bool_field_with_default", config.require_bool),
        ("bool_field_optional", config.get_bool),
        ("bool_field_optional_with_default", config.get_bool),
    ]:
        assert Confy.config_getter_func(dcfield=dcfields[field_name], config=config) == config_func


@pytest.mark.usefixtures("config_fields")
def test_field_is_bool(request) -> None:
    dcfields = request.getfixturevalue("config_fields")
    for field_name in [
        "bool_field",
        "bool_field_with_default",
        "bool_field_optional",
        "bool_field_optional_with_default",
    ]:
        assert Confy.field_type(field_type=dcfields[field_name].type) is bool


@pytest.mark.usefixtures("config_fields")
def test_field_is_int(request) -> None:
    dcfields = request.getfixturevalue("config_fields")
    for field_name in [
        "int_field",
        "int_field_with_default",
        "int_field_optional",
        "int_field_optional_with_default",
    ]:
        assert Confy.field_type(field_type=dcfields[field_name].type) is int


@pytest.mark.usefixtures("config_fields")
def test_field_is_collection(request) -> None:
    dcfields = request.getfixturevalue("config_fields")
    for field_name in dcfields.keys():
        if dcfields[field_name].name.startswith(("dict", "list", "tuple")):
            assert Confy.field_type(field_type=dcfields[field_name].type) is Collection


@pytest.mark.usefixtures("config_fields")
def test_field_is_secret(request) -> None:
    dcfields = request.getfixturevalue("config_fields")
    for field_name in dcfields.keys():
        if field_name.startswith("secret"):
            assert Confy.is_secret(field_type=dcfields[field_name].type)


@pytest.mark.usefixtures("config_fields")
def test_config_getter_func_dicts(request) -> None:
    dcfields = request.getfixturevalue("config_fields")
    config = pulumi.Config()
    for field_name, config_func in [
        ("dict_field", config.require_object),
        ("dict_field_with_default", config.require_object),
        ("dict_field_optional", config.get_object),
        ("dict_field_optional_with_default", config.get_object),
    ]:
        assert Confy.config_getter_func(dcfield=dcfields[field_name], config=config) == config_func

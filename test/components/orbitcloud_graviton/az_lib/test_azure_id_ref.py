import pytest

from orbitcloud_graviton.az_lib.types import parse_stack_reference
from orbitcloud_graviton.pulumi_mocks import set_mocks

set_mocks()


def test_stack_ref_parse_too_few_parts_exception():
    with pytest.raises(ValueError):
        parse_stack_reference("stack://too_few/parts")


def test_stack_ref_parse_too_many_parts_exception():
    with pytest.raises(ValueError):
        parse_stack_reference("stack://too/many/parts/here/now")


def test_stack_ref_with_nested_output():
    assert parse_stack_reference("stack://project/stack/output.path") == (
        "mock-org/project/stack",
        "output",
        "path",
    )


def test_stack_ref_with_deeply_nested_output():
    assert parse_stack_reference("stack://project/stack/output.path.to.something") == (
        "mock-org/project/stack",
        "output",
        "path.to.something",
    )


def test_stack_ref_parse_with_org():
    assert parse_stack_reference("stack://org/project/stack/output") == (
        "org/project/stack",
        "output",
        None,
    )


def test_stack_ref_with_default_org():
    # Org is configured in set_mocks()
    assert parse_stack_reference("stack://project/stack/output") == (
        "mock-org/project/stack",
        "output",
        None,
    )

"""Tests for the Logic Apps workflow component."""

from uuid import UUID

import pulumi
import pytest
from pulumi_azure_native import logic

from orbitcloud_graviton.pulumi_mocks import set_mocks

set_mocks()

from orbitcloud_graviton.az_logic import (  # noqa: E402
    EMPTY_WORKFLOW_DEFINITION,
    LogicWorkflow,
    LogicWorkflowAccessControlConfig,
    LogicWorkflowConfig,
)
from orbitcloud_graviton.pulumi_lib import AzureStack  # noqa: E402

WORKSPACE_ID = (
    "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg"
    "/providers/Microsoft.OperationalInsights/workspaces/law"
)


def _make_stack(**overrides) -> AzureStack:
    defaults = {
        "subscription_id": UUID("00000000-0000-0000-0000-000000000000"),
        "tenant_id": UUID("00000000-0000-0000-0000-000000000000"),
        "location": "northeurope",
        "workload_name": "testworkload",
        "env": "test",
        "skip_exports": True,
    }
    defaults.update(overrides)
    return AzureStack(**defaults)


# --- Config ---


def test_config_defaults() -> None:
    config = LogicWorkflowConfig()

    assert config.state is logic.WorkflowState.ENABLED
    assert config.system_assigned_identity is True
    assert config.definition == EMPTY_WORKFLOW_DEFINITION


def test_config_definition_is_not_shared_between_instances() -> None:
    first = LogicWorkflowConfig()
    second = LogicWorkflowConfig()

    first.definition["actions"]["mutated"] = {}

    assert "mutated" not in second.definition["actions"]
    assert "mutated" not in EMPTY_WORKFLOW_DEFINITION["actions"]


def test_config_forbids_extra() -> None:
    with pytest.raises(ValueError):
        LogicWorkflowConfig.model_validate({"unknown": "value"})


def test_access_control_config_forbids_extra() -> None:
    with pytest.raises(ValueError):
        LogicWorkflowAccessControlConfig.model_validate({"nope": ["10.0.0.0/8"]})


# --- Resources ---


@pulumi.runtime.test
def test_workflow_created() -> None:
    component = LogicWorkflow(stack=_make_stack(), config=LogicWorkflowConfig())

    assert isinstance(component.workflow, logic.Workflow)


@pulumi.runtime.test
def test_workflow_name_follows_naming_convention() -> None:
    component = LogicWorkflow(stack=_make_stack(), config=LogicWorkflowConfig(name="orders"))

    assert component.workflow._name == "logic-orders-test-neu-01"


@pulumi.runtime.test
def test_system_assigned_identity_by_default() -> None:
    component = LogicWorkflow(stack=_make_stack(), config=LogicWorkflowConfig())

    def check(identity) -> None:
        assert identity["type"] == logic.ManagedServiceIdentityType.SYSTEM_ASSIGNED

    return component.workflow.identity.apply(check)  # type: ignore[return-value]


@pulumi.runtime.test
def test_identity_can_be_disabled() -> None:
    component = LogicWorkflow(
        stack=_make_stack(),
        config=LogicWorkflowConfig(system_assigned_identity=False),
    )

    def check(identity) -> None:
        assert identity is None

    return component.workflow.identity.apply(check)  # type: ignore[return-value]


@pulumi.runtime.test
def test_access_control_ip_ranges() -> None:
    component = LogicWorkflow(
        stack=_make_stack(),
        config=LogicWorkflowConfig(
            access_control=LogicWorkflowAccessControlConfig(triggers=["10.0.0.0/8"]),
        ),
    )

    def check(access_control) -> None:
        ranges = access_control.triggers.allowed_caller_ip_addresses
        assert [r.address_range for r in ranges] == ["10.0.0.0/8"]
        assert access_control.contents is None

    return component.workflow.access_control.apply(check)  # type: ignore[return-value]


@pulumi.runtime.test
def test_diagnostics_created_with_workspace() -> None:
    component = LogicWorkflow(
        stack=_make_stack(),
        config=LogicWorkflowConfig(log_workspace_id=WORKSPACE_ID),
    )

    assert component.diagnostic_settings is not None


@pulumi.runtime.test
def test_no_diagnostics_without_workspace() -> None:
    component = LogicWorkflow(stack=_make_stack(), config=LogicWorkflowConfig())

    assert component.diagnostic_settings is None

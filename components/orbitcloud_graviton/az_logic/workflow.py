"""Azure Logic Apps (Consumption) workflow component."""

from copy import deepcopy
from typing import Any

import pulumi
from pulumi_azure_native import logic, monitor
from pydantic import BaseModel, ConfigDict, Field

from orbitcloud_graviton.az_iam.assignment import IamAssignmentConfig, iam_assignment
from orbitcloud_graviton.az_lib.types import AzureIdRef
from orbitcloud_graviton.az_monitor import diagnostic_setting
from orbitcloud_graviton.pulumi_lib import AzureStack

# Empty but valid Logic App definition -- a workflow with no trigger and no action.
EMPTY_WORKFLOW_DEFINITION: dict[str, Any] = {
    "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
    "contentVersion": "1.0.0.0",
    "parameters": {},
    "triggers": {},
    "actions": {},
    "outputs": {},
}

LOG_CATEGORIES: list[str] = ["WorkflowRuntime"]


class LogicWorkflowAccessControlConfig(BaseModel):
    """Caller IP restrictions for the workflow control planes.

    Each list holds CIDR ranges or single addresses. An empty list locks the
    section down completely, while ``None`` leaves Azure's default in place.
    """

    triggers: list[str] | None = None
    contents: list[str] | None = None
    actions: list[str] | None = None
    workflow_management: list[str] | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class LogicWorkflowConfig(BaseModel):
    name: str | None = None

    definition: dict[str, Any] = Field(default_factory=lambda: deepcopy(EMPTY_WORKFLOW_DEFINITION))
    parameters: dict[str, Any] | None = None
    state: logic.WorkflowState = logic.WorkflowState.ENABLED

    integration_account_id: AzureIdRef | None = None
    access_control: LogicWorkflowAccessControlConfig | None = None

    # Identity
    system_assigned_identity: bool = True
    user_assigned_identity_ids: list[AzureIdRef] | None = None

    log_workspace_id: AzureIdRef | None = None
    azure_permissions: list[IamAssignmentConfig] | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class LogicWorkflow(pulumi.ComponentResource):
    """A Consumption-tier Logic App workflow with diagnostics and IAM wiring."""

    def __init__(
        self,
        stack: AzureStack,
        config: LogicWorkflowConfig,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        self.stack: AzureStack = stack
        self.config: LogicWorkflowConfig = config

        super().__init__(
            "Graviton:LogicWorkflow",
            name=f"logic-{config.name or stack.workload_name}-{stack.env}",
            props=None,
            opts=opts,
        )

        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts1=opts, opts2=pulumi.ResourceOptions(parent=self)
        )

        self.workflow: logic.Workflow = self._workflow()
        self._azure_permissions()
        self.diagnostic_settings: monitor.DiagnosticSetting | None = self._diagnostic_settings()

        self._outputs()

    @property
    def name(self) -> pulumi.Output[str]:
        return self.workflow.name

    @property
    def id(self) -> pulumi.Output[str]:
        return self.workflow.id

    def _workflow_name(self) -> str:
        return self.stack.name_for(
            resource_type=logic.Workflow,
            workload_name=self.config.name or self.stack.workload_name,
        )

    def _identity(self) -> logic.ManagedServiceIdentityArgs | None:
        if self.config.user_assigned_identity_ids:
            return logic.ManagedServiceIdentityArgs(
                type=logic.ManagedServiceIdentityType.USER_ASSIGNED,
                user_assigned_identities=[str(i) for i in self.config.user_assigned_identity_ids],
            )
        if self.config.system_assigned_identity:
            return logic.ManagedServiceIdentityArgs(
                type=logic.ManagedServiceIdentityType.SYSTEM_ASSIGNED
            )
        return None

    @staticmethod
    def _access_policy(
        ranges: list[str] | None,
    ) -> logic.FlowAccessControlConfigurationPolicyArgs | None:
        if ranges is None:
            return None
        return logic.FlowAccessControlConfigurationPolicyArgs(
            allowed_caller_ip_addresses=[logic.IpAddressRangeArgs(address_range=r) for r in ranges]
        )

    def _access_control(self) -> logic.FlowAccessControlConfigurationArgs | None:
        if not self.config.access_control:
            return None

        access = self.config.access_control
        return logic.FlowAccessControlConfigurationArgs(
            triggers=self._access_policy(access.triggers),
            contents=self._access_policy(access.contents),
            actions=self._access_policy(access.actions),
            workflow_management=self._access_policy(access.workflow_management),
        )

    def _workflow(self) -> logic.Workflow:
        workflow_name: str = self._workflow_name()

        return logic.Workflow(
            resource_name=workflow_name,
            args=logic.WorkflowArgs(
                workflow_name=workflow_name,
                resource_group_name=self.stack.resource_group.name,
                location=self.stack.resource_group.location,
                tags=self.stack.tags,
                state=self.config.state,
                definition=self.config.definition,
                parameters=self.config.parameters,
                identity=self._identity(),
                access_control=self._access_control(),
                integration_account=logic.ResourceReferenceArgs(
                    id=str(self.config.integration_account_id)
                )
                if self.config.integration_account_id
                else None,
            ),
            opts=self._opts,
        )

    def _azure_permissions(self) -> None:
        if not self.config.azure_permissions:
            return

        for perm in self.config.azure_permissions:
            iam_assignment(
                stack=self.stack,
                config=IamAssignmentConfig(
                    name_prefix=f"{perm.name_prefix}-{self.config.name}"
                    if perm.name_prefix
                    else self.config.name,
                    role=perm.role,
                    scope=perm.scope,
                    description=perm.description,
                ),
                principal_id=self.workflow.identity.principal_id,
                opts=pulumi.ResourceOptions(parent=self.workflow, delete_before_replace=True),
            )

    def _diagnostic_settings(self) -> monitor.DiagnosticSetting | None:
        if not self.config.log_workspace_id:
            return None

        return diagnostic_setting(
            resource=self.workflow,
            log_workspace_id=str(self.config.log_workspace_id),
            metric_categories=["AllMetrics"],
            log_categories=LOG_CATEGORIES,
            opts=pulumi.ResourceOptions(parent=self.workflow),
        )

    def _outputs(self) -> None:
        self.register_outputs({"workflow": self.workflow})

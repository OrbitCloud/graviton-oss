from typing import Literal

from pulumi_azure_native.app import v20241002preview as app
from pydantic import BaseModel, ConfigDict, Field

from .scaling import CustomRuleTypes


class JobTriggerBase(BaseModel):
    replica_timeout_seconds: int = Field(
        ..., description="The maximum time in seconds to wait for a replica to complete."
    )
    failed_replica_retry_count: int | None = Field(
        default=None, description="The number of times to retry a failed replica."
    )
    parallelism: int = Field(
        default=1,
        description="The number of replicas to run per execution. For most jobs, set the value to 1.",
    )
    replica_completion_count: int = Field(
        default=1,
        description="The number of replicas to complete successfully for the execution to succeed. Most be equal or less than the parallelism. For most jobs, set the value to 1.",
    )

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class JobManualTrigger(JobTriggerBase):
    trigger_type: Literal[app.TriggerType.MANUAL]

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    def manual_args(self) -> app.JobConfigurationManualTriggerConfigArgs:
        return app.JobConfigurationManualTriggerConfigArgs(
            parallelism=self.parallelism,
            replica_completion_count=self.replica_completion_count,
        )


class JobScheduledTrigger(JobTriggerBase):
    trigger_type: Literal[app.TriggerType.SCHEDULE]
    cron: str

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    def schedule_args(self) -> app.JobConfigurationScheduleTriggerConfigArgs:
        return app.JobConfigurationScheduleTriggerConfigArgs(
            parallelism=self.parallelism,
            replica_completion_count=self.replica_completion_count,
            cron_expression=self.cron,
        )


class JobEventTriggerScaling(BaseModel):
    min_executions: int = Field(
        default=0,
        description="Minimum number of job executions that are created for a trigger, default 0",
    )
    max_executions: int = Field(
        default=100,
        description="Maximum number of job executions that are created for a trigger, default 100.",
    )
    polling_interval_seconds: int = Field(
        default=30, description="The interval in seconds to poll for replica status."
    )
    rules: dict[str, CustomRuleTypes]

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class JobEventTrigger(JobTriggerBase):
    trigger_type: Literal[app.TriggerType.EVENT]
    scale: JobEventTriggerScaling

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    def event_args(self) -> app.JobConfigurationEventTriggerConfigArgs:
        rules = []
        for name, rule in self.scale.rules.items():
            rules.append(
                app.JobScaleRuleArgs(
                    name=name,
                    type=rule.rule_type,
                    # Waiting for 2024-08-02-preview to become available
                    # identity="system",
                    auth=[
                        app.ScaleRuleAuthArgs(
                            secret_ref=auth.secret_ref,
                            trigger_parameter=auth.trigger_parameter,
                        )
                        for auth in rule.auth or []
                    ],
                    metadata=rule.metadata.model_dump(by_alias=True)
                    if isinstance(rule.metadata, BaseModel)
                    else rule.metadata,
                )
            )

        return app.JobConfigurationEventTriggerConfigArgs(
            parallelism=self.parallelism,
            replica_completion_count=self.replica_completion_count,
            scale=app.JobScaleArgs(
                min_executions=self.scale.min_executions,
                max_executions=self.scale.max_executions,
                polling_interval=self.scale.polling_interval_seconds,
                rules=rules,
            ),
        )

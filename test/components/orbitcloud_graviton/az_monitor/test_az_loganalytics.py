import pulumi
from pulumi_azure_native import operationalinsights

from orbitcloud_graviton.az_monitor import LogWorkspaceConfig, log_workspace
from orbitcloud_graviton.pulumi_lib import AzureStack
from orbitcloud_graviton.pulumi_mocks import set_mocks

set_mocks()


@pulumi.runtime.test
def test_log_logworkspace(stack: AzureStack) -> None:
    config = LogWorkspaceConfig(
        public_network_access_for_ingestion=operationalinsights.PublicNetworkAccessType.DISABLED,
        public_network_access_for_query=operationalinsights.PublicNetworkAccessType.DISABLED,
        retention_in_days=60,
        daily_quota_gb=5,
        disable_local_auth=True,
    )

    log: operationalinsights.Workspace = log_workspace(
        config=config,
        stack=stack,
    )

    assert isinstance(log, operationalinsights.Workspace)

    def check_parameters(args):
        (
            log_location,
            log_tags,
            public_network_access_for_ingestion,
            public_network_access_for_query,
            retention_in_days,
            disable_local_auth,
            daily_quota_gb,
        ) = args

        assert log_location == stack.location

        # Check that all tags are present if they are defined
        if stack.tags and log_tags:
            for key, value in log_tags.items():
                assert log_tags.get(key) == value, f"{key} tag is not set to {value}"

        assert log._name.startswith(f"log-{stack.workload_name}-{stack.env}-neu")

        assert (
            public_network_access_for_ingestion
            == operationalinsights.PublicNetworkAccessType.DISABLED
        )
        assert (
            public_network_access_for_query == operationalinsights.PublicNetworkAccessType.DISABLED
        )
        assert retention_in_days == 60
        assert disable_local_auth is True
        assert daily_quota_gb == 5

    pulumi.Output.all(
        log.location,
        log.tags,
        log.public_network_access_for_ingestion,
        log.public_network_access_for_query,
        log.retention_in_days,
        log.features.disable_local_auth,
        log.workspace_capping.daily_quota_gb,
    ).apply(check_parameters)

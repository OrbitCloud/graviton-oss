from typing import List, Optional

import pulumi

from orbitcloud_graviton.az_iam import iam_assignment
from orbitcloud_graviton.entra import EntraApp, EntraAppConfig, WorkloadIdentityConfig
from orbitcloud_graviton.pulumi_lib import (
    AzureStack,
    EntraStack,
    PulumiConfig,
    generate_stack_schema,
    get_azure_stack,
    get_entra_stack,
)


class WorkloadIdentitiesConfig(PulumiConfig):
    identities: Optional[List[WorkloadIdentityConfig]] = None


def deploy() -> None:
    generate_stack_schema(model=WorkloadIdentitiesConfig, output_file=".stack_schema.json")

    config: WorkloadIdentitiesConfig = WorkloadIdentitiesConfig.model_validate({})
    entra_config: EntraStack = EntraStack.model_validate({})

    # Get Azure Stack and export resource group
    stack: AzureStack = get_azure_stack()
    entra_config: EntraStack = get_entra_stack()

    ##########################################
    #   Entra Apps for VCS credentials
    ##########################################
    if config.identities:
        for cred in config.identities:
            entra_app = EntraApp(
                stack=stack.model_copy(update={"exports_prefix": cred.workload.credential_type}),
                entra=entra_config,
                config=EntraAppConfig(
                    name=f"{cred.workload.credential_type}",
                    federated_credentials=cred.workload.credentials(),
                ),
            )

            for permission in cred.azure_permissions or []:
                iam_assignment(
                    stack=stack,
                    config=permission,
                    principal_id=entra_app.service_principal.id,
                    opts=pulumi.ResourceOptions(
                        parent=entra_app.service_principal, delete_before_replace=True
                    ),
                )

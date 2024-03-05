from typing import List, Optional, Union

import pulumi
from pydantic import BaseModel, Field

from orbitcloud_graviton.az_iam import IamAssignmentConfig, iam_assignment
from orbitcloud_graviton.entra import (
    EntraApp,
    EntraAppConfig,
    GitHubOIDCCredentials,
)
from orbitcloud_graviton.entra.oidc_providers import (
    AzureDevOpsOIDCCredentials,
    PulumiOIDCCredentials,
)
from orbitcloud_graviton.pulumi_lib import (
    AzureBase,
    EntraBase,
    PulumiConfig,
    generate_stack_schema,
    get_azure_stack,
    get_entra_stack,
)


class WorkloadCredentials(BaseModel):
    workload: Union[AzureDevOpsOIDCCredentials, GitHubOIDCCredentials, PulumiOIDCCredentials] = (
        Field(default=..., discriminator="credential_type")
    )
    azure_permissions: Optional[list[IamAssignmentConfig]] = None


class WorkloadIdentitiesConfig(PulumiConfig):
    identities: Optional[List[WorkloadCredentials]] = None


def deploy() -> None:
    generate_stack_schema(model=WorkloadIdentitiesConfig, output_file=".stack_schema.json")

    config: WorkloadIdentitiesConfig = WorkloadIdentitiesConfig.model_validate({})
    entra_config: EntraBase = EntraBase.model_validate({})

    # Get Azure Stack and export resource group
    stack: AzureBase = get_azure_stack()
    entra_config: EntraBase = get_entra_stack()

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
                    principal=entra_app.service_principal,
                    opts=pulumi.ResourceOptions(
                        parent=entra_app.service_principal, delete_before_replace=True
                    ),
                )

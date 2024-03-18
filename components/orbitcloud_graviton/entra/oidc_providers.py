from typing import List, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from orbitcloud_graviton.az_iam.assignment import IamAssignmentConfig
from orbitcloud_graviton.entra.entra_app import FederatedCredentialsConfig


class PulumiOIDCCredentials(BaseModel):
    credential_type: Literal["pulumi"] = "pulumi"
    organization: str

    def credentials(self) -> list[FederatedCredentialsConfig]:
        return [
            FederatedCredentialsConfig(
                issuer="https://api.pulumi.com/oidc",
                audiences=[self.organization],
                subject=f"pulumi:environments:org:{self.organization}:env:<yaml>",
                description="Pulumi Environment Credentials used for infrastructure deployments",
            )
        ]

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class AzureDevOpsOIDCCredentials(BaseModel):
    credential_type: Literal["azuredevops"] = "azuredevops"
    ado_org_id: UUID
    ado_org_name: str
    ado_project_name: str
    ado_service_connection_name: str

    def credentials(self) -> list[FederatedCredentialsConfig]:
        return [
            FederatedCredentialsConfig(
                issuer=f"https://vstoken.dev.azure.com/{self.ado_org_id}",
                audiences=["api://AzureADTokenExchange"],
                subject=f"sc://{self.ado_org_name}/{self.ado_project_name}/{self.ado_service_connection_name}",
                description="Azure DevOps Service Connection Credentials",
            )
        ]

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class GitHubOIDCCredentials(BaseModel):
    credential_type: Literal["github"] = "github"
    github_org: str
    repo: str

    # At least one of the following must be set
    environments: Optional[List[str]] = None
    branches: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    pull_request: Optional[bool] = False

    def credentials(self) -> list[FederatedCredentialsConfig]:
        prefix: str = f"repo:{self.github_org}/{self.repo}"
        creds = []

        self.environments = [] if not self.environments else self.environments
        self.branches = [] if not self.branches else self.branches
        self.tags = [] if not self.tags else self.tags

        subjects = []
        subjects.extend(
            [f"{prefix}:environment:{environment}" for environment in self.environments]
        )
        subjects.extend([f"{prefix}:ref:refs/heads/{branch}" for branch in self.branches])
        subjects.extend([f"{prefix}:ref:refs/tags/{tag}" for tag in self.tags])
        subjects.extend([f"{prefix}:pull_request"] if self.pull_request else [])

        for subject in subjects:
            creds.append(
                FederatedCredentialsConfig(
                    issuer="https://token.actions.githubusercontent.com",
                    audiences=["api://AzureADTokenExchange"],
                    subject=subject,
                )
            )

        return creds

    @model_validator(mode="after")
    def at_least_one_gh_param(m: "GitHubOIDCCredentials") -> "GitHubOIDCCredentials":
        if sum([not m.environments, not m.branches, not m.pull_request, not m.tags]) == 4:
            raise ValueError(
                "One and only one of the following must be set: environments, branches, pull_request, tags"
            )

        return m

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class WorkloadIdentityConfig(BaseModel):
    workload: Union[AzureDevOpsOIDCCredentials, GitHubOIDCCredentials, PulumiOIDCCredentials] = (
        Field(default=..., discriminator="credential_type")
    )
    azure_permissions: Optional[list[IamAssignmentConfig]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

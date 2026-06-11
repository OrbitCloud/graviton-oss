from typing import Literal
from uuid import UUID

import pulumi
from pydantic import BaseModel, ConfigDict, Field, model_validator

from orbitcloud_graviton.az_iam.assignment import IamAssignmentConfig
from orbitcloud_graviton.az_lib import fmt_name
from orbitcloud_graviton.entra.entra_app import FederatedCredentialsConfig
from orbitcloud_graviton.pulumi_lib import AzureStack


class PulumiEscOidcProvider(BaseModel):
    credential_type: Literal["pulumi"] = "pulumi"
    organization: str
    environment_name: str
    allowed_in_childs: bool | None = False
    allowed_pulumi_logins: list[str] | None = None

    def _subject_attrs(self) -> tuple[list, list]:
        attrs: list[tuple[str, str]] = [("pulumi.organization.login", self.organization)]

        if self.allowed_in_childs:
            attrs.append(("rootEnvironment.name", self.environment_name))
        else:
            attrs.append(("currentEnvironment.name", self.environment_name))

        subject: str = "pulumi:environments:" + ":".join([f"{key}={value}" for key, value in attrs])

        if self.allowed_pulumi_logins:
            attrs.append(("pulumi.user.login", ""))
            subjects = [
                f"{subject}:pulumi.user.login:{login}" for login in self.allowed_pulumi_logins
            ]
        else:
            subjects: list[str] = [subject]

        return subjects, attrs

    def credentials(self) -> list[FederatedCredentialsConfig]:
        return [
            FederatedCredentialsConfig(
                issuer="https://api.pulumi.com/oidc",
                audiences=[self.organization],
                subject=f"pulumi:environments:org:{self.organization}:env:<yaml>",
                description="Pulumi Environment Credentials used for infrastructure deployments",
            )
        ]

        # Waiting for https://github.com/pulumi/pulumi/issues/14509
        # return [
        #     FederatedCredentialsConfig(
        #         issuer="https://api.pulumi.com/oidc",
        #         audiences=[self.organization],
        #         subject=_subject,
        #         description="Pulumi Environment Credentials used for infrastructure deployments",
        #     )
        #     for _subject in self._subject_attrs()[0]
        # ]

    def azure_login(self, stack: AzureStack, client_id: pulumi.Output[str] | str) -> dict:
        return {
            "login": {
                "fn::open::azure-login": {
                    "clientId": client_id,
                    "tenantId": str(object=stack.tenant_id),
                    "subscriptionId": str(object=stack.subscription_id),
                    "oidc": True,
                    # Waiting for https://github.com/pulumi/pulumi/issues/14509
                    # "subjectAttributes": [attr[0] for attr in self._subject_attrs()[1]],
                }
            }
        }

    def azure_env_vars(self) -> dict[str, str]:
        return {
            "ARM_USE_OIDC": "true",
            "ARM_CLIENT_ID": "${azure.login.clientId}",
            "ARM_TENANT_ID": "${azure.login.tenantId}",
            "ARM_OIDC_TOKEN": "${azure.login.oidc.token}",
            "ARM_SUBSCRIPTION_ID": "${azure.login.subscriptionId}",
        }

    def azure_pulumi_config(self) -> dict[str, str]:
        return {
            "azure-native:tenantId": "${azure.login.tenantId}",
            "azure-native:subscriptionId": "${azure.login.subscriptionId}",
            "azuread:tenantId": "${azure.login.tenantId}",
        }

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
    repo: str | list[str]

    # At least one of the following must be set
    environments: list[str] | None = None
    branches: list[str] | None = None
    tags: list[str] | None = None
    pull_request: bool | None = False

    def credentials(self) -> list[FederatedCredentialsConfig]:
        repos = self.repo if isinstance(self.repo, list) else [self.repo]
        creds = []

        for repo in repos:
            prefix: str = f"repo:{self.github_org}/{repo}"

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
                        name=fmt_name(subject),
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
    workload: AzureDevOpsOIDCCredentials | GitHubOIDCCredentials | PulumiEscOidcProvider = Field(
        default=..., discriminator="credential_type"
    )
    azure_permissions: list[IamAssignmentConfig] | None = None
    # Free-text "Internal notes" for the generated app registration. Defaults to
    # the IaC-managed marker when not supplied.
    internal_notes: str | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

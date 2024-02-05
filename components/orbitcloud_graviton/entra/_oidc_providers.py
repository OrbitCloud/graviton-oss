from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from orbitcloud_graviton.entra._entra_app import FederatedCredentials


class PulumiOIDCCredentials(BaseModel):
    organization: str

    def credentials(self) -> list[FederatedCredentials]:
        return [
            FederatedCredentials(
                issuer="https://api.pulumi.com/oidc",
                audiences=[self.organization],
                subject=f"pulumi:environments:org:{self.organization}:env:<yaml>",
                description="Pulumi Environment Credentials used for infrastructure deployments",
            )
        ]


class GitHubOIDCCredentials(BaseModel):
    github_org: str
    repo: str

    # At least one of the following must be set
    environments: Optional[List[str]] = Field(default_factory=list)
    branches: Optional[List[str]] = Field(default_factory=list)
    tags: Optional[List[str]] = Field(default_factory=list)
    pull_request: Optional[bool] = False

    def credentials(self) -> list[FederatedCredentials]:
        prefix: str = f"repo:{self.github_org}/{self.repo}:"
        creds = []
        self.environments = self.environments or []
        self.branches = self.branches or []
        self.tags = self.tags or []
        for subject in (
            [f"{prefix}:environment:{environment}" for environment in self.environments]
            + [f"{prefix}/ref:refs/heads/{branch}" for branch in self.branches]
            + [f"{prefix}/ref:refs/tags/{tag}" for tag in self.tags]
            + [f"{prefix}/pull_request"]
            if self.pull_request
            else []
        ):
            creds.append(
                FederatedCredentials(
                    issuer="https://github.com",
                    audiences=["api://AzureADTokenExchange"],
                    subject=subject,
                )
            )
        return creds

    @model_validator(mode="after")
    def at_least_one_gh_param(m: "GitHubOIDCCredentials") -> "GitHubOIDCCredentials":
        if sum([not m.environments, not m.branches, not m.pull_request, not m.tags]) < 4:
            raise ValueError(
                "One and only one of the following must be set: gh_environment, gh_branch, gh_pull_request, gh_tag"
            )

        return m

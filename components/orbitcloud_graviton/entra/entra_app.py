from typing import List, Literal, Optional, Self

import pulumi
import pulumi_azuread as azuread
from pulumi import ComponentResource
from pulumiverse_time import Rotating
from pydantic import BaseModel, ConfigDict, Field

from orbitcloud_graviton.az_iam.assignment import IamAssignmentConfig, iam_assignment
from orbitcloud_graviton.az_lib.helpers import fmt_name
from orbitcloud_graviton.pulumi_lib import AzureStack, EntraStack
from orbitcloud_graviton.pulumi_lib.types import TimeFromNow

from .roles import get_entra_role_id_by_name


class ClientCredentialsConfig(BaseModel):
    display_name: str
    expires_after: TimeFromNow = TimeFromNow(after="6M")
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class FederatedCredentialsConfig(BaseModel):
    issuer: str
    audiences: List[str]
    subject: str
    description: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class EntraAppConfig(
    BaseModel,
):
    name: str
    display_name: Optional[str] = None
    audience: Optional[
        Literal[
            "AzureADMyOrg",
            "AzureADMultipleOrgs",
            "AzureADandPersonalMicrosoftAccount",
            "PersonalMicrosoftAccount",
        ]
    ] = "AzureADMyOrg"
    client_credentials: Optional[List[ClientCredentialsConfig]] = Field(default_factory=list)
    federated_credentials: Optional[List[FederatedCredentialsConfig]] = Field(default_factory=list)
    owners: Optional[List[str]] = Field(default_factory=list)

    entra_roles: Optional[List[str]] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class EntraApp(ComponentResource):
    def __init__(
        self,
        stack: AzureStack,
        entra: EntraStack,
        config: EntraAppConfig,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        self.stack: AzureStack = stack
        self.entra: EntraStack = entra
        self.config: EntraAppConfig = config

        super().__init__(
            "Graviton:Entra:EntraApp",
            name=f"ea-{self.config.name}-{self.stack.workload_name}-{self.stack.env}",
            props=None,
            opts=opts,
        )
        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts, pulumi.ResourceOptions(parent=self)
        )

        self.app: azuread.Application = self._app()
        self.service_principal: azuread.ServicePrincipal = self._service_principal()
        self.client_credentials: List[azuread.ApplicationPassword] = self._client_credentials()
        self.federated_credentials: list[azuread.ApplicationFederatedIdentityCredential] = (
            self._federated_credentials()
        )
        self.entra_roles = self._entra_roles()

        self._outputs()

    def _app(self) -> azuread.Application:
        return azuread.Application(
            resource_name=f"ea-{self.config.name}-{self.stack.workload_name}-{self.stack.env}",
            display_name=f"{self.config.name}-{self.stack.workload_name}-{self.stack.env}",
            sign_in_audience=self.config.audience,
            owners=self.config.owners,
            opts=self._opts,
        )

    def _service_principal(self) -> azuread.ServicePrincipal:
        return azuread.ServicePrincipal(
            resource_name=f"sp-{self.config.name}-{self.stack.env}",
            client_id=self.app.client_id,
            opts=self._opts,
        )

    def _client_credentials(self) -> List[azuread.ApplicationPassword]:
        creds = []
        if not self.config.client_credentials:
            return []
        for cred in self.config.client_credentials:
            rotation: Rotating = cred.expires_after.Rotating(
                resource_name=f"rotate-{self.config.name}-{cred.display_name}-{self.stack.workload_name}-{self.stack.env}",
                opts=self._opts,
            )

            creds.append(
                azuread.ApplicationPassword(
                    resource_name=f"eapw-{self.config.name}-{self.stack.workload_name}-{self.stack.env}",
                    display_name=cred.display_name,
                    application_id=self.app.id,
                    rotate_when_changed={
                        "rotation": rotation.id.apply(lambda id: id),
                    },
                    opts=self._opts,
                )
            )
        return creds

    def _federated_credentials(self) -> list[azuread.ApplicationFederatedIdentityCredential]:
        return (
            [
                azuread.ApplicationFederatedIdentityCredential(
                    f"oidc-{self.config.name}-{self.stack.env}",
                    display_name=f"oidc-{self.config.name}",
                    application_id=self.app.id,
                    issuer=cred.issuer,
                    audiences=cred.audiences,
                    subject=cred.subject,
                    description=cred.description,
                    opts=self._opts,
                )
                for cred in self.config.federated_credentials
            ]
            if self.config.federated_credentials
            else []
        )

    def _entra_roles(self) -> None:
        if not self.config.entra_roles:
            return
        for role in self.config.entra_roles:
            azuread.DirectoryRoleAssignment(
                resource_name=f"entrarole-{fmt_name(role)}-{fmt_name(self.config.name)}-{self.stack.env}",
                args=azuread.DirectoryRoleAssignmentArgs(
                    principal_object_id=self.service_principal.id,
                    role_id=get_entra_role_id_by_name(role_name=role),
                ),
                opts=self._opts,
            )

    def azure_permissions(self, assignments: List[IamAssignmentConfig]) -> Self:
        for perm in assignments:
            iam_assignment(
                stack=self.stack,
                config=perm,
                principal_id=self.service_principal.id,
                opts=pulumi.ResourceOptions(
                    parent=self.service_principal,
                    delete_before_replace=True,
                ),
            )
        return self

    def _outputs(self) -> None:
        self.register_outputs(
            {
                "app": self.app,
                "service_principal": self.service_principal,
            }
        )

        def _federated_credentials_outputs() -> list:
            return (
                [
                    {
                        "issuer": cred.issuer,
                        "audiences": cred.audiences,
                        "subject": cred.subject,
                    }
                    for cred in self.federated_credentials
                ]
                if self.federated_credentials
                else []
            )

        self.stack.export(
            exports={
                "entra_app": {
                    "app": {
                        "id": self.app.id,
                        "client_id": self.app.object_id,
                    },
                    "service_principal": {
                        "id": self.service_principal.id,
                        "client_id": self.service_principal.client_id,
                        "tenant_id": self.service_principal.application_tenant_id,
                    },
                    "federated_credentials": _federated_credentials_outputs(),
                },
            }
        )

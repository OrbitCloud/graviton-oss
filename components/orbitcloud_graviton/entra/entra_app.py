from typing import List, Literal, Optional

import pulumi
import pulumi_azuread as azuread
import pulumiverse_time as time
from pulumi import ComponentResource
from pulumi_azure_native import authorization
from pydantic import BaseModel, ConfigDict, Field

from orbitcloud_graviton.az_iam import iam_assignment
from orbitcloud_graviton.pulumi_lib import AzureBase, EntraBase


class ClientCredentials(BaseModel):
    display_name: str
    expires_after_months: Optional[int] = 12
    model_config = ConfigDict(arbitrary_types_allowed=True)


class AzureRbacPermission(BaseModel):
    role_name: str
    scope: str

    model_config = ConfigDict(arbitrary_types_allowed=True)


class FederatedCredentials(BaseModel):
    issuer: str
    audiences: List[str]
    subject: str
    description: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class EntraAppConfig(BaseModel):
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
    client_credentials: Optional[List[ClientCredentials]] = Field(default_factory=list)
    federated_credentials: Optional[List[FederatedCredentials]] = Field(default_factory=list)

    azure_permissions: Optional[List[AzureRbacPermission]] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class EntraApp(ComponentResource):
    def __init__(
        self,
        stack: AzureBase,
        entra: EntraBase,
        config: EntraAppConfig,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        self.stack = stack
        self.entra = entra
        self.config = config

        super().__init__(
            "Graviton:Entra:EntraApp",
            name=f"ea-{self.stack.workload_name}",
            props=None,
            opts=opts,
        )
        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts, pulumi.ResourceOptions(parent=self)
        )

        self.app: azuread.Application = self._app()
        self.service_principal: azuread.ServicePrincipal = self._service_principal()
        self.client_credentials = self._client_credentials()
        self.federated_credentials = self._federated_credentials()

        self._azure_permissions()

        self._outputs()

    def _azure_permissions(
        self,
    ) -> List[authorization.RoleAssignment]:
        if not self.config.azure_permissions:
            return []

        perms = []
        for perm in self.config.azure_permissions:
            perms.append(
                iam_assignment(
                    resource_name=f"iamrole-sp-{perm.role_name}-{self.config.name}",
                    role_name=perm.role_name,
                    scope=perm.scope,
                    principal=self.service_principal,
                    opts=self._opts._merge_instance(
                        pulumi.ResourceOptions(parent=self.service_principal)
                    ),
                )
            )
        return perms

    def _app(self) -> azuread.Application:
        return azuread.Application(
            f"ea-{self.config.name}",
            display_name=self.config.display_name or self.config.name,
            sign_in_audience=self.config.audience,
            opts=self._opts,
        )

    def _service_principal(self) -> azuread.ServicePrincipal:
        return azuread.ServicePrincipal(
            f"sp-{self.config.name}",
            client_id=self.app.client_id,
            opts=self._opts,
        )

    def _client_credentials(self) -> List[azuread.ApplicationPassword]:
        creds = []
        if not self.config.client_credentials:
            return []
        for cred in self.config.client_credentials:
            rotation: time.Rotating = time.Rotating(
                resource_name=f"secret-{cred.display_name}",
                rotation_months=cred.expires_after_months,
            )

            creds.append(
                azuread.ApplicationPassword(
                    f"secret-{self.config.name}",
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
                    f"oidc-{self.config.name}",
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

    def _outputs(self) -> None:
        self.register_outputs(
            {
                "app": self.app,
                "service_principal": self.service_principal,
            }
        )

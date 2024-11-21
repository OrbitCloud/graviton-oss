from pathlib import PosixPath
from typing import List, Literal, Optional, Self

import pulumi
import pulumi_azuread as azuread
from pulumi import ComponentResource
from pulumi_random import RandomUuid, RandomUuidArgs
from pulumi_std import filebase64
from pulumiverse_time import Rotating
from pydantic import BaseModel, ConfigDict, Field, FilePath, field_validator

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
    name: str | None = None
    issuer: str
    audiences: List[str]
    subject: str
    description: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class EntraAppAppRole(BaseModel):
    allowed_member_types: list[Literal["User", "Application"]]
    description: str
    display_name: str
    value: str

    def id(self, opts: pulumi.ResourceOptions | None = None) -> pulumi.Output[str]:
        return RandomUuid(
            resource_name=f"app-role-{fmt_name(self.display_name)}",
            args=RandomUuidArgs(
                keepers={"display_name": self.display_name},
            ),
            opts=opts,
        ).result

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class EntraAppBranding(BaseModel):
    privacy_statement_url: str | None = None
    support_url: str | None = None
    terms_of_service_url: str | None = None
    homepage_url: str | None = None
    logo_file: FilePath | None = None

    @field_validator("logo_file")
    def validate_logo_file(cls, value: PosixPath) -> PosixPath | None:
        if value:
            _value = str(value)
            if not _value.endswith((".gif", ".jpg", ".jpeg", ".png")):
                raise ValueError("Logo file must be a gif, jpg, jpeg, or png file")
            # Enforce location within assets folder
            if (
                (not _value.startswith("assets/") and not _value.startswith("./assets/"))
                or ".." in _value
                or "~" in _value
                or "//" in _value
            ):
                raise ValueError("Logo file must reside in the ./assets folder")
        return value

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class EntraAppGraphApiPermissions(BaseModel):
    scopes: list[str]
    resource_app_id: str = "00000003-0000-0000-c000-000000000000"

    def resource_args(self) -> List[azuread.ApplicationRequiredResourceAccessResourceAccessArgs]:
        graph_permissions: dict[str, dict[str, str]] = {
            "GroupMember.Read.All": {
                "id": "bc024368-1153-4739-b217-4326f2e966d0",
                "type": "Scope",
            },
            "User.Read": {
                "id": "e1fe6dd8-ba31-4d61-89e7-88639da4683d",
                "type": "Scope",
            },
        }

        try:
            resources: List[azuread.ApplicationRequiredResourceAccessResourceAccessArgs] = [
                azuread.ApplicationRequiredResourceAccessResourceAccessArgs(
                    id=graph_permissions[perm]["id"],
                    type=graph_permissions[perm]["type"],
                )
                for perm in self.scopes
            ]
        except KeyError as e:
            raise KeyError(f"Permission {e} hasn't been defined in graph_permissions") from e

        return resources

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class EntraAppAuthentication(BaseModel):
    audience: Optional[
        Literal[
            "AzureADMyOrg",
            "AzureADMultipleOrgs",
            "AzureADandPersonalMicrosoftAccount",
            "PersonalMicrosoftAccount",
        ]
    ] = "AzureADMyOrg"
    identifier_uris: list[str] | None = None
    logout_url: str | None = None
    redirect_uris: list[str] | None = None
    branding: EntraAppBranding = EntraAppBranding()
    graph_permissions: EntraAppGraphApiPermissions | None = None
    group_membership_claims: (
        list[Literal["SecurityGroup", "DirectoryRole", "ApplicationGroup", "All"]] | None
    ) = None
    app_roles: list[EntraAppAppRole] | None = None
    assignment_required: bool = False

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class EntraAppConfig(
    BaseModel,
):
    name: str
    display_name: Optional[str] = None
    client_credentials: Optional[List[ClientCredentialsConfig]] = Field(default_factory=list)
    federated_credentials: Optional[List[FederatedCredentialsConfig]] = Field(default_factory=list)
    owners: Optional[List[str]] = Field(default_factory=list)
    authentication: EntraAppAuthentication = EntraAppAuthentication()

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
        self.client_credentials: None | dict[str, azuread.ApplicationPassword] = (
            self._client_credentials()
        )
        self.federated_credentials: list[azuread.ApplicationFederatedIdentityCredential] = (
            self._federated_credentials()
        )
        self.entra_roles = self._entra_roles()

        self._outputs()

    def _app(self) -> azuread.Application:
        return azuread.Application(
            resource_name=f"ea-{self.config.name}-{self.stack.workload_name}-{self.stack.env}",
            args=azuread.ApplicationArgs(
                display_name=self.config.display_name
                or f"{self.config.name}-{self.stack.workload_name}-{self.stack.env}",
                sign_in_audience=self.config.authentication.audience,
                owners=self.config.owners,
                identifier_uris=self.config.authentication.identifier_uris,
                logo_image=filebase64(
                    str(object=self.config.authentication.branding.logo_file)
                ).result
                if self.config.authentication.branding.logo_file
                else None,
                web=azuread.ApplicationWebArgs(
                    redirect_uris=self.config.authentication.redirect_uris,
                    homepage_url=self.config.authentication.branding.homepage_url,
                    logout_url=self.config.authentication.logout_url,
                ),
                terms_of_service_url=self.config.authentication.branding.terms_of_service_url,
                privacy_statement_url=self.config.authentication.branding.privacy_statement_url,
                required_resource_accesses=[
                    azuread.ApplicationRequiredResourceAccessArgs(
                        resource_app_id=self.config.authentication.graph_permissions.resource_app_id,
                        resource_accesses=self.config.authentication.graph_permissions.resource_args(),
                    )
                ]
                if self.config.authentication.graph_permissions
                else None,
                app_roles=[
                    azuread.ApplicationAppRoleArgs(
                        allowed_member_types=role.allowed_member_types,
                        description=role.description,
                        display_name=role.display_name,
                        id=role.id(opts=self._opts),
                        value=role.value,
                    )
                    for role in self.config.authentication.app_roles or []
                ],
                group_membership_claims=self.config.authentication.group_membership_claims,
            ),
            opts=self._opts,
        )

    def _service_principal(self) -> azuread.ServicePrincipal:
        return azuread.ServicePrincipal(
            resource_name=f"sp-{self.config.name}-{self.stack.env}",
            args=azuread.ServicePrincipalArgs(
                client_id=self.app.client_id,
                app_role_assignment_required=self.config.authentication.assignment_required,
            ),
            opts=self._opts,
        )

    def _client_credentials(self) -> None | dict[str, azuread.ApplicationPassword]:
        creds: dict[str, azuread.ApplicationPassword] = {}
        if not self.config.client_credentials:
            return None
        for cred in self.config.client_credentials:
            rotation: Rotating = cred.expires_after.Rotating(
                resource_name=f"rotate-{self.config.name}-{cred.display_name}-{self.stack.workload_name}-{self.stack.env}",
                opts=self._opts,
            )

            creds[cred.display_name] = azuread.ApplicationPassword(
                resource_name=f"eapw-{self.config.name}-{self.stack.workload_name}-{self.stack.env}",
                args=azuread.ApplicationPasswordInitArgs(
                    display_name=cred.display_name,
                    application_id=self.app.id,
                    end_date_relative=cred.expires_after,
                    rotate_when_changed={
                        "rotation": rotation.id.apply(lambda id: id),
                    },
                ),
                opts=self._opts,
            )
        return creds

    def _federated_credentials(self) -> list[azuread.ApplicationFederatedIdentityCredential]:
        return (
            [
                azuread.ApplicationFederatedIdentityCredential(
                    f"oidc-{cred.name or self.config.name}-{self.stack.env}",
                    display_name=f"oidc-{cred.name or self.config.name}",
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
                principal_id=self.service_principal.object_id,
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
                    "client_credentials": {
                        cred_name: {
                            "display_name": cred.display_name,
                            "secret": cred.value,
                            "expires": cred.end_date,
                            "expires_after": cred.end_date_relative,
                        }
                        for cred_name, cred in self.client_credentials.items()
                    }
                    if self.client_credentials
                    else None,
                },
            }
        )

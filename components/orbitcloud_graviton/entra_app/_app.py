from typing import Optional

import pulumi
from pulumi_azuread import (
    Application,
    ApplicationFederatedIdentityCredential,
    ServicePrincipal,
)

from orbitcloud_graviton.az_iam import role_assignment, roles

from ._credentials import federated_credentials


def application(app_name) -> Application:
    return Application(
        f"ea-{app_name}",
        display_name=f"{app_name}",
        sign_in_audience="AzureADMyOrg",
    )


def service_principal(
    app_name: str,
    app: Application,
    opts: Optional[pulumi.ResourceOptions] = None,
) -> ServicePrincipal:
    return ServicePrincipal(
        f"sp-{app_name}",
        client_id=app.client_id,
        opts=opts,
    )


def deployment_oidc_app(
    workload_name: str,
    pulumi_org: str,
    subscription_id: str,
) -> tuple[Application, ServicePrincipal, ApplicationFederatedIdentityCredential]:
    entra_oidc_app: tuple[
        Application, ServicePrincipal, ApplicationFederatedIdentityCredential
    ] = oidc_app(
        app_name=f"pulumi-{workload_name}",
        issuer="https://api.pulumi.com/oidc",
        audiences=[pulumi_org],
        description="Pulumi Deployment Credentials",
        subject=f"pulumi:environments:org:{pulumi_org}:env:<yaml>",
        scope=f"/subscriptions/{subscription_id}",
        role_definition_id=roles.contributor(subscription_id=subscription_id),
    )
    return entra_oidc_app


def oidc_app(
    app_name: str,
    issuer: str,
    audiences: list[str],
    subject: str,
    scope: str,
    role_definition_id: str,
    description: str,
) -> tuple[Application, ServicePrincipal, ApplicationFederatedIdentityCredential]:
    app: Application = application(app_name)
    sp: ServicePrincipal = service_principal(
        app_name, app, opts=pulumi.ResourceOptions(parent=app)
    )
    cred: ApplicationFederatedIdentityCredential = federated_credentials(
        app=app,
        credential_name=app_name,
        issuer=issuer,
        audiences=audiences,
        description=description,
        subject=subject,
        opts=pulumi.ResourceOptions(parent=app),
    )
    role_assignment(
        principal=sp,
        principal_name=app_name,
        role_definition_id=role_definition_id,
        scope=scope,
        opts=pulumi.ResourceOptions(parent=sp),
    )

    return app, sp, cred

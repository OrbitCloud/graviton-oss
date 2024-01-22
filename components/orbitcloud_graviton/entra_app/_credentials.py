from typing import Optional

import pulumi
from pulumi_azuread import (
    Application,
    ApplicationFederatedIdentityCredential,
)


def federated_credentials(
    app: Application,
    credential_name: str,
    issuer: str,
    audiences: list[str],
    description: str,
    subject: str,
    opts: Optional[pulumi.ResourceOptions] = None,
):
    return ApplicationFederatedIdentityCredential(
        resource_name=f"oidc-{credential_name}",
        display_name=f"oidc-{credential_name}",
        application_id=app.object_id.apply(
            lambda object_id: f"/applications/{object_id}"
        ),
        audiences=audiences,
        issuer=issuer,
        description=description,
        subject=subject,
        opts=opts,
    )

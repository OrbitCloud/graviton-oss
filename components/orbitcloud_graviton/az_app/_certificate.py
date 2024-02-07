from typing import Optional

import pulumi
from pulumi_azure_native.app import v20230501 as app
from pydantic import Base64Str, BaseModel, Field, SecretStr

from orbitcloud_graviton.pulumi_lib import AzureBase


class CertificateConfig(BaseModel):
    name: str = Field(pattern=r"^[a-z0-9](?:[a-z0-9\-\.]*[a-z0-9])?$", max_length=60)
    contents: SecretStr
    password: SecretStr = Field(Base64Str)


def certificate(
    stack: AzureBase,
    cert: CertificateConfig,
    environment: app.ManagedEnvironment,
    opts: Optional[pulumi.ResourceOptions] = None,
) -> app.Certificate:
    certificate = app.Certificate(
        resource_name=cert.name,
        certificate_name=cert.name,
        environment_name=environment.name,
        resource_group_name=stack.resource_group.name,
        location=stack.location,
        properties=app.CertificatePropertiesArgs(
            password=cert.password.get_secret_value(),
            value=cert.contents.get_secret_value(),
        ),
        opts=opts,
    )

    return certificate

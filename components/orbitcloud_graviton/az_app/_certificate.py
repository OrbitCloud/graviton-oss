import re
from typing import Optional

import pulumi
from pulumi_azure_native.app import v20230501 as app
from pydantic import BaseModel, SecretStr, field_validator

from orbitcloud_graviton.pulumi_lib import AzureBase


class CertificateConfig(BaseModel):
    certificate_name: str
    certificate_value: SecretStr
    certificate_password: SecretStr
    environment_name: str

    @field_validator("certificate_name")
    def certificate_name_format(cls, v):
        # Check if the value matches the required patterns
        pattern = r"^[a-z0-9](?:[a-z0-9\-\.]*[a-z0-9])?$"
        if not re.match(pattern, v):
            raise ValueError(
                "must consist of lower case alphanumeric characters, '-' or '.', and must start and end with an alphanumeric character"
            )
        # Check if the value is not longer than 60 characters
        if len(v) > 60:
            raise ValueError("must be a maximum of 60 characters long")
        return v


def certificate(
    stack: AzureBase,
    config: CertificateConfig,
    opts: Optional[pulumi.ResourceOptions] = None,
) -> app.Certificate:
    certificate = app.Certificate(
        resource_name=config.certificate_name,
        certificate_name=config.certificate_name,
        environment_name=config.environment_name,
        resource_group_name=stack.resource_group.name,
        location=stack.location,
        properties=app.CertificatePropertiesArgs(
            password=config.certificate_password.get_secret_value(), value=config.certificate_value.get_secret_value()
        ),
        opts=opts,
    )

    return certificate

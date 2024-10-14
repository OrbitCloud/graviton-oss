import pulumi
from pulumi_azure_native.app import v20240301 as app
from pydantic import BaseModel, Field, SecretStr

from orbitcloud_graviton.pulumi_lib import AzureStack
from orbitcloud_graviton.pulumi_lib.helpers import fmt_name


class CertificateConfig(BaseModel):
    name: str = Field(pattern=r"^[a-z0-9](?:[a-z0-9\-\.]*[a-z0-9])?$", max_length=60)
    cert_value: SecretStr
    cert_pass: SecretStr


def certificate(
    stack: AzureStack,
    cert: CertificateConfig,
    environment: app.ManagedEnvironment,
    opts: pulumi.ResourceOptions | None = None,
) -> app.Certificate:
    certificate = app.Certificate(
        resource_name=stack.name_for(
            resource_type=app.Certificate, workload_name=fmt_name(cert.name)
        ),
        certificate_name=cert.name,
        environment_name=environment.name,
        resource_group_name=stack.resource_group.name,
        location=stack.location,
        properties=app.CertificatePropertiesArgs(
            password=cert.cert_pass.get_secret_value(),
            value=cert.cert_value.get_secret_value(),
        ),
        opts=opts,
    )

    return certificate


def managed_certificate(
    stack: AzureStack,
    custom_domain: str,
    environment: app.ManagedEnvironment,
    opts: pulumi.ResourceOptions | None = None,
) -> app.ManagedCertificate | None:
    app.ManagedCertificate(
        resource_name="cert",
        args=app.ManagedCertificateArgs(
            resource_group_name=stack.resource_group.name,
            environment_name=environment.name,
            managed_certificate_name=custom_domain,
            properties=app.ManagedCertificatePropertiesArgs(
                domain_control_validation=app.ManagedCertificateDomainControlValidation.HTTP,
                subject_name=custom_domain,
            ),
            location=stack.location,
        ),
        opts=pulumi.ResourceOptions.merge(
            pulumi.ResourceOptions(custom_timeouts=pulumi.CustomTimeouts(create="1m")), opts
        ),
    )

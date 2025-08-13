import pulumi
from pulumi_azure_native.app import v20241002preview as app
from pydantic import BaseModel, Field, SecretStr

from orbitcloud_graviton.pulumi_lib import AzureStack
from orbitcloud_graviton.pulumi_lib.helpers import fmt_name

from .outputs import ContainerAppEnvOutput


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
    environment: ContainerAppEnvOutput,
    opts: pulumi.ResourceOptions | None = None,
) -> app.ManagedCertificate | None:
    app.ManagedCertificate(
        resource_name=stack.name_for(
            resource_type=app.ManagedCertificate, workload_name=fmt_name(custom_domain)
        ),
        args=app.ManagedCertificateArgs(
            resource_group_name=environment.resource_group_name,
            environment_name=environment.name,
            managed_certificate_name=f"cert-{custom_domain.replace('.', '-')}",
            properties=app.ManagedCertificatePropertiesArgs(
                domain_control_validation=app.ManagedCertificateDomainControlValidation.HTTP,
                subject_name=custom_domain,
            ),
            location=stack.location,
        ),
        opts=opts,
        # pulumi.ResourceOptions.merge(
        #     pulumi.ResourceOptions(custom_timeouts=pulumi.CustomTimeouts(create="1m")), opts
        # ),
    )

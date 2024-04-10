from typing import List, Optional

import pulumi
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from pulumi import ComponentResource, Output, ResourceOptions
from pulumi_azure_native import authorization, keyvault
from pulumi_random import RandomPassword, RandomPasswordArgs
from pulumi_tls import PrivateKey, PrivateKeyArgs
from pulumiverse_acme import (
    Certificate,
    CertificateArgs,
    CertificateDnsChallengeArgs,
    Registration,
    RegistrationArgs,
)
from pulumiverse_acme import (
    Provider as AcmeProvider,
)
from pydantic import BaseModel, ConfigDict, EmailStr

from orbitcloud_graviton.az_iam import IamAssignmentConfig, iam_assignment
from orbitcloud_graviton.az_keyvault.secret import KeyvaultSecretConfig, keyvault_secret
from orbitcloud_graviton.az_lib import AzureIdRef
from orbitcloud_graviton.entra import ClientCredentialsConfig, EntraApp, EntraAppConfig
from orbitcloud_graviton.pulumi_lib import AzureBase, EntraBase
from orbitcloud_graviton.pulumi_lib.azure_base import get_azure_stack, get_entra_stack
from orbitcloud_graviton.pulumi_lib.config import PulumiConfig
from orbitcloud_graviton.pulumi_lib.helpers import fmt_name
from orbitcloud_graviton.pulumi_lib.stack_schema import generate_stack_schema
from orbitcloud_graviton.pulumi_lib.types import TimeFromNow, email_random_plus


class AcmeSslConfig(BaseModel):
    dns_zone_id: AzureIdRef
    dns_zone_resource_group_name: Optional[str] = None
    dns_zone_name: str

    acme_account_email: EmailStr
    keyvault_id: Optional[AzureIdRef] = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class AcmeSslBaseConfig(PulumiConfig):
    cert_request: AcmeSslConfig


class AcmeSsl(ComponentResource):
    def __init__(
        self,
        stack: AzureBase,
        entra_config: EntraBase,
        config: AcmeSslConfig,
        entra_app: Optional[EntraApp] = None,
        opts: Optional[ResourceOptions] = None,
    ) -> None:
        self.stack: AzureBase = stack
        self.config: AcmeSslConfig = config
        self.entra_config: EntraBase = entra_config

        super().__init__(
            "Graviton:AcmeSsl",
            name=f"acmessl-{stack.workload_name}-{stack.env}",
            props=None,
            opts=pulumi.ResourceOptions.merge(
                pulumi.ResourceOptions(additional_secret_outputs=["cert_value"]), opts
            ),
        )

        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts1=opts, opts2=pulumi.ResourceOptions(parent=self)
        )

        self.entra_app: EntraApp = entra_app or self._entra_app()
        self.azure_permissions: List[authorization.RoleAssignment] = self._azure_permissions()

        self.acme_account_email: EmailStr | Output[EmailStr] = email_random_plus(
            email=self.config.acme_account_email
        )
        self.pulumi_acme_provider: AcmeProvider = self._pulumi_acme_provider()
        self.pfx_pass: str = self._pfx_pass()
        self.registration: Registration = self._registration()
        self.certificate: Certificate = self._certificate()

        self.keyvault_secret: keyvault.Secret | None = self._keyvault_secret()

        self._outputs()

    def _entra_app(self) -> EntraApp:
        return EntraApp(
            stack=self.stack,
            entra=self.entra_config,
            config=EntraAppConfig(
                name="acmessl",
                client_credentials=[
                    ClientCredentialsConfig(
                        display_name="acmessl-credentials",
                        expires_after=TimeFromNow(after="1M"),
                    )
                ],
            ),
            opts=self._opts,
        )

    def _azure_permissions(self) -> List[authorization.RoleAssignment]:
        if isinstance(self.config.dns_zone_id, Output):
            scope = self.config.dns_zone_id.apply(lambda id: f"{id}/txt/_acme-challenge")
        else:
            scope = f"{self.config.dns_zone_id}/txt/_acme-challenge"

        perms = [
            {
                "name_prefix": fmt_name(["acme", self.config.dns_zone_name]),
                "role": "DNS Zone Contributor",
                "description": "Allows management of _acme-challenge TXT record.",
                "scope": scope,
            },
            {
                "name_prefix": fmt_name(["acme", self.config.dns_zone_name]),
                "role": "Reader",
                "description": "Allows reading of the DNS Zone.",
                "scope": self.config.dns_zone_id,
            },
        ]

        return [
            iam_assignment(
                stack=self.stack,
                principal_id=self.entra_app.service_principal.id,
                config=IamAssignmentConfig(**perm),
                opts=pulumi.ResourceOptions.merge(
                    self._opts, pulumi.ResourceOptions(self.entra_app)
                ),
            )
            for perm in perms
        ]

    def _dns_challenge_args(self) -> dict:
        return {
            "AZURE_AUTH_METHOD": "env",
            "AZURE_CLIENT_ID": self.entra_app.app.client_id,
            "AZURE_CLIENT_SECRET": self.entra_app.client_credentials[0].value,
            "AZURE_TENANT_ID": str(self.stack.tenant_id),
            "AZURE_SUBSCRIPTION_ID": str(self.stack.subscription_id),
            "AZURE_ZONE_NAME": self.config.dns_zone_name,
            "AZURE_RESOURCE_GROUP": self.config.dns_zone_resource_group_name
            or self.stack.resource_group.name,
        }

    def _pfx_pass(self) -> str:
        return RandomPassword(
            resource_name=f"acme-pfx-pass-{fmt_name(self.config.dns_zone_name)}",
            args=RandomPasswordArgs(length=32),
            opts=self._opts,
        ).result

    def _pulumi_acme_provider(self) -> AcmeProvider:
        return AcmeProvider(
            resource_name=f"acme-provider-{fmt_name(self.config.dns_zone_name)}",
            server_url="https://acme-v02.api.letsencrypt.org/directory",
            opts=self._opts,
        )

    def _registration_pkey(self) -> PrivateKey:
        return PrivateKey(
            resource_name=f"acme-account-key-{fmt_name(self.config.acme_account_email)}",
            args=PrivateKeyArgs(
                algorithm="RSA",
                rsa_bits=2048,
            ),
            opts=self._opts,
        )

    def _registration(self) -> Registration:
        return Registration(
            resource_name=f"acme-reg-{fmt_name(self.config.acme_account_email)}",
            args=RegistrationArgs(
                email_address=self.acme_account_email,
                account_key_pem=self._registration_pkey().private_key_pem,
            ),
            opts=pulumi.ResourceOptions.merge(
                self._opts, pulumi.ResourceOptions(provider=self.pulumi_acme_provider)
            ),
        )

    def _certificate(self) -> Certificate:
        return Certificate(
            resource_name=f"acme-cert-{fmt_name(self.config.dns_zone_name)}",
            args=CertificateArgs(
                common_name=f"*.{self.config.dns_zone_name}",
                account_key_pem=self.registration.account_key_pem,
                certificate_p12_password=self.pfx_pass,
                min_days_remaining=30,
                key_type="2048",
                pre_check_delay=60,
                revoke_certificate_on_destroy=False,
                dns_challenges=[
                    CertificateDnsChallengeArgs(
                        provider="azuredns",
                        config=self._dns_challenge_args(),
                    )
                ],
            ),
            opts=pulumi.ResourceOptions.merge(
                self._opts,
                pulumi.ResourceOptions(
                    parent=self.registration,
                    additional_secret_outputs=[
                        "certificate_pem",
                        "certificate",
                        "issuer_pem",
                        "certificate_p12",
                    ],
                    provider=self.pulumi_acme_provider,
                ),
            ),
        )

    def _keyvault_secret(self) -> keyvault.Secret | None:
        if not self.config.keyvault_id:
            return None

        secret: keyvault.Secret = keyvault_secret(
            stack=self.stack,
            config=KeyvaultSecretConfig(
                name=f"cert-{fmt_name(self.config.dns_zone_name)}",
                keyvault_id=self.config.keyvault_id,
                value=self.certificate.certificate_p12,
                content_type="application/x-pkcs12",
            ),
            opts=pulumi.ResourceOptions(parent=self.certificate, delete_before_replace=True),
        )

        return secret

    def _outputs(self) -> None:
        self.register_outputs(
            {
                "app": self.entra_app.app,
                "service_principal": self.entra_app.service_principal,
                "azure_permissions": self.azure_permissions,
                "certificate": self.certificate,
            },
        )

        # Azure has a strict requirement for PEM encoded private keys to be in PKCS8 format,
        # https://learn.microsoft.com/en-us/azure/key-vault/certificates/certificate-scenarios#formats-of-import-we-support
        x509_pkcs8_pem: Output[str] = pulumi.Output.all(
            cert=self.certificate.certificate_pem, key=self.certificate.private_key_pem
        ).apply(
            lambda args: args["cert"]
            + serialization.load_pem_private_key(
                args["key"].encode(), password=None, backend=default_backend()
            )
            .private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            .decode()
        )

        self.stack.export(
            exports={
                "certificate": {
                    "common_name": self.config.dns_zone_name,
                    "wildcard": True,
                    "expires": self.certificate.certificate_not_after,
                    "acme_account": {
                        "email": self.acme_account_email,
                        "pem_key": self.registration.account_key_pem,
                    },
                    "pem": {
                        "cert": self.certificate.certificate_pem,
                        "private_key": self.certificate.private_key_pem,
                        "issuer": self.certificate.issuer_pem,
                        "fullchain": pulumi.Output.concat(
                            self.certificate.certificate_pem,
                            self.certificate.issuer_pem,
                        ),
                        "azure_x509_pkcs8": x509_pkcs8_pem,
                    },
                    "pfx": {
                        "value": self.certificate.certificate_p12,
                        "pass": self.pfx_pass,
                    },
                    "keyvault_secret": {
                        "id": self.keyvault_secret.id,
                        "name": self.keyvault_secret.name,
                        "secret_uri": self.keyvault_secret.properties.secret_uri,
                        "secret_uri_with_version": self.keyvault_secret.properties.secret_uri_with_version,
                    }
                    if self.keyvault_secret
                    else None,
                }
            }
        )


def deploy() -> None:
    generate_stack_schema(model=AcmeSslBaseConfig, output_file=".stack_schema.json")
    stack: AzureBase = get_azure_stack()
    entra: EntraBase = get_entra_stack()
    config: AcmeSslBaseConfig = AcmeSslBaseConfig.model_validate({})

    AcmeSsl(
        stack=stack,
        entra_config=entra,
        config=config.cert_request,
    )

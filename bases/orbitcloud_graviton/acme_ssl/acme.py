from typing import List, Optional

import pulumi
import pulumiverse_time as time
from pulumi import ComponentResource, Output, ResourceOptions
from pulumi_azure_native import authorization, keyvault
from pulumi_command import local
from pulumi_random import RandomPassword
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from orbitcloud_graviton.az_iam import IamAssignmentConfig, iam_assignment
from orbitcloud_graviton.az_keyvault.secret import KeyvaultSecretConfig, keyvault_secret
from orbitcloud_graviton.az_lib import AzureIdRef
from orbitcloud_graviton.entra import ClientCredentialsConfig, EntraApp, EntraAppConfig
from orbitcloud_graviton.pulumi_lib import AzureBase, EntraBase
from orbitcloud_graviton.pulumi_lib.helpers import fmt_name


class AcmeSslConfig(BaseModel):
    dns_zone_id: AzureIdRef
    dns_zone_name: str

    ssl_contact_email: EmailStr
    use_staging_issuer: Optional[bool] = Field(
        default=False, description="Use Let's Encrypt staging issuer for testing."
    )

    keyvault_id: Optional[AzureIdRef] = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class AcmeSsl(ComponentResource):
    def __init__(
        self,
        stack: AzureBase,
        entra_config: EntraBase,
        config: AcmeSslConfig,
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

        self.entra_app: EntraApp = self._entra_app()
        self.azure_permissions: List[authorization.RoleAssignment] = self._azure_permissions()
        self.trigger: time.Rotating = self._cert_trigger()
        self.pfx_pass: str = self._pfx_pass()
        self.certificate: local.Command = self._wildcard_certificate()
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
                        expires_after_months=1,
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
                principal=self.entra_app.service_principal,
                config=IamAssignmentConfig(**perm),
                opts=pulumi.ResourceOptions.merge(
                    self._opts, pulumi.ResourceOptions(self.entra_app)
                ),
            )
            for perm in perms
        ]

    def _pfx_pass(self) -> str:
        return RandomPassword(
            resource_name="acme-pfx-pass",
            length=32,
            keepers={"trigger": self.trigger.id.apply(lambda id: id)},
            opts=self._opts,
        ).result

    def _lego_env_vars(self) -> dict:
        return {
            # "AZURE_AUTH_METHOD": "cli",
            "AZURE_AUTH_METHOD": "env",
            "AZURE_CLIENT_ID": self.entra_app.app.client_id,
            "AZURE_CLIENT_SECRET": self.entra_app.client_credentials[0].value,
            "AZURE_TENANT_ID": str(self.stack.tenant_id),
            "AZURE_SUBSCRIPTION_ID": str(self.stack.subscription_id),
            "AZURE_ZONE_NAME": self.config.dns_zone_name,
            "AZURE_RESOURCE_GROUP": self.stack.resource_group.name,
            "AZURE_PROPAGATION_TIMEOUT": "65",
            "LEGO_PFX_PASSWORD": self.pfx_pass,
            "LEGO_PFX_FORMAT": "SHA256",
        }

    def _cert_trigger(self) -> time.Rotating:
        return time.Rotating(
            resource_name=f"cert-rotation-{fmt_name(self.config.dns_zone_name)}",
            # Let's Encrypt certs are valid for 90 days and we can renew them 30 days before expiry
            rotation_days=62,
            opts=self._opts,
        )

    def _lego_cmd_args(self) -> str:
        staging_server: str = (
            "--server=https://acme-staging-v02.api.letsencrypt.org/directory"
            if self.config.use_staging_issuer
            else ""
        )
        cmd_create: str = (
            f"lego --accept-tos {staging_server}"
            f" --domains '*.{self.config.dns_zone_name}'"
            f" --email {self.config.ssl_contact_email}"
            " --dns azuredns --pfx run"
        )

        return cmd_create

    def _wildcard_certificate(self) -> local.Command:
        cert_path: str = f".lego/certificates/_.{self.config.dns_zone_name}.pfx"

        cert_script = local.Command(
            resource_name="cmd-lego-cert",
            environment=self._lego_env_vars(),
            create=self._lego_cmd_args(),
            delete="rm -rf .lego",
            triggers=[{"rotating": self.trigger.id}],
            opts=pulumi.ResourceOptions.merge(
                self._opts,
                pulumi.ResourceOptions(
                    delete_before_replace=True,
                    depends_on=[
                        self.entra_app.app,
                        self.azure_permissions[0],
                        self.azure_permissions[1],
                        self.entra_app.client_credentials[0],
                    ],
                ),
            ),
        )

        pulumi.Output.all(cert_script.stdout, cert_script.stderr).apply(
            lambda x: print(f"lego cli output: {x[0]}\n{x[1]}")
        )

        cmd = local.Command(
            resource_name="cmd-cert-output",
            create=f"base64 -i '{cert_path}'",
            triggers=[
                {
                    "cert_script_stdout": cert_script.stdout,
                    "cert_script_stderr": cert_script.stderr,
                }
            ],
            opts=pulumi.ResourceOptions(
                parent=cert_script, depends_on=[cert_script], additional_secret_outputs=["stdout"]
            ),
        )
        return cmd

    def _keyvault_secret(self) -> keyvault.Secret | None:
        if not self.config.keyvault_id:
            return None

        secret = keyvault_secret(
            stack=self.stack,
            config=KeyvaultSecretConfig(
                name=f"wcplus-{fmt_name(self.config.dns_zone_name)}",
                keyvault_id=self.config.keyvault_id,
                value=self.certificate.stdout,
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
                "pfx_pass": self.pfx_pass,
                "certificate": self.certificate,
            },
        )

        self.stack.export(
            exports={
                "ssl_cert": {
                    "value": self.certificate.stdout,
                    "pass": self.pfx_pass,
                    "keyvault_secret_id": self.keyvault_secret.id if self.keyvault_secret else None,
                }
            }
        )

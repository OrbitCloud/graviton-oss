from typing import Optional

from pulumi import ComponentResource, ResourceOptions
from pydantic import BaseModel, ConfigDict

from orbitcloud_graviton.az_iam import IamAssignmentConfig, iam_assignment
from orbitcloud_graviton.az_lib import AzureIdRef
from orbitcloud_graviton.entra import ClientCredentials, EntraApp, EntraAppConfig
from orbitcloud_graviton.pulumi_lib import AzureBase, EntraBase
from orbitcloud_graviton.pulumi_lib.helpers import dash_formatted


class AcmeAppConfig(BaseModel):
    dns_zone_id: AzureIdRef
    zone_name: str

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class AcmeEntraApp(ComponentResource):
    def __init__(
        self,
        stack: AzureBase,
        entra_config: EntraBase,
        config: AcmeAppConfig,
        opts: Optional[ResourceOptions] = None,
    ) -> None:
        self.stack: AzureBase = stack
        self.config: AcmeAppConfig = config
        self.entra_config: EntraBase = entra_config

        self.entra_app: EntraApp = self._entra_app()

        super().__init__(
            "Graviton:AcmeEntraApp", name=f"acme-{stack.workload_name}", props=None, opts=opts
        )

        self._outputs()

    def _entra_app(self) -> EntraApp:
        return EntraApp(
            stack=self.stack,
            entra=self.entra_config,
            config=EntraAppConfig(
                name=f"certbot-{self.stack.env}",
                client_credentials=[
                    ClientCredentials(
                        display_name="certbot",
                        expires_after_months=1,
                    )
                ],
            ),
        )

    def _permissions(self) -> None:
        iam_assignment(
            stack=self.stack,
            principal=self.entra_app.service_principal,
            config=IamAssignmentConfig(
                name_prefix=dash_formatted(["acme", self.config.zone_name]),
                role="DNS Zone Contributor",
                scope=str(
                    f"{self.config.dns_zone_id}/txt/_acme-challenge.${self.config.zone_name}"
                ),
                description="Allows management of _acme-challenge TXT record.",
            ),
        )

    def _outputs(self) -> None:
        self.register_outputs({"app": self.entra_app})

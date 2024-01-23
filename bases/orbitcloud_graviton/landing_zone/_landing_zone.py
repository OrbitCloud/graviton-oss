from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pulumi
from pulumi_azure_native import authorization, containerregistry, keyvault, resources

from orbitcloud_graviton.az_acr.registry import az_containerregistry
from orbitcloud_graviton.az_keyvault import az_keyvault
from orbitcloud_graviton.az_lib import Confy, StackConfig
from orbitcloud_graviton.az_resources.resource_group import (
    az_resource_group_from_config,
)
from orbitcloud_graviton.entra_app import deployment_oidc_app
from orbitcloud_graviton.pulumi_lib import print_pulumi_esc_oidc_yaml


@dataclass(kw_only=True, frozen=True)
class LandingZoneConfig(StackConfig):
    tags: Optional[Dict[str, str]] = None
    cr_ip_allow_list: Optional[List[str]] = field(default_factory=list)
    cr_public_network_access: Optional[str] = field(
        default=containerregistry.PublicNetworkAccess.DISABLED
    )


def deploy_landing_zone() -> None:
    config: LandingZoneConfig = Confy(LandingZoneConfig).populate()
    provider: authorization.GetClientConfigResult = authorization.get_client_config()

    # Resource Group
    az_rg: resources.ResourceGroup = az_resource_group_from_config(config=config)
    pulumi.export("resource_group_name", az_rg.name)

    # Pulumi Deployments Entra App - OIDC
    esc_app, _, _ = deployment_oidc_app(
        workload_name=config.workload_name,
        pulumi_org=pulumi.get_organization(),
        subscription_id=provider.subscription_id,
    )

    # Container Registry
    az_cr: containerregistry.Registry = az_containerregistry(
        workload_name=config.workload_name,
        env=config.env,
        location=config.location,
        resource_group=az_rg,
        ip_allow_list=config.cr_ip_allow_list,
        public_network_access=config.cr_public_network_access,
        opts=pulumi.ResourceOptions(parent=az_rg),
    )
    pulumi.export("containerregistry_server", az_cr.login_server)
    pulumi.export("containerregistry_id", az_cr.id)

    # Keyvault
    az_kv: keyvault.Vault = az_keyvault(
        workload_name=config.workload_name,
        env=config.env,
        location=config.location,
        resource_group=az_rg,
        tenant_id=provider.tenant_id,
        opts=pulumi.ResourceOptions(parent=az_rg),
    )
    pulumi.export("keyvault_name", az_kv.name)
    pulumi.export("keyvault_id", az_kv.id)

    pulumi.Output.all(
        esc_app.client_id, provider.tenant_id, provider.subscription_id
    ).apply(func=print_pulumi_esc_oidc_yaml)

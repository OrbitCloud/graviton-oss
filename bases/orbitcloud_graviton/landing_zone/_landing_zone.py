import pulumi
from pulumi_azure_native import containerregistry, keyvault, resources

from orbitcloud_graviton.az_acr.registry import (
    ContainerRegistryConfig,
    az_containerregistry,
)
from orbitcloud_graviton.az_keyvault import az_keyvault
from orbitcloud_graviton.az_network import VnetConfig
from orbitcloud_graviton.az_resources import az_resource_group_from_config
from orbitcloud_graviton.entra_app import deployment_oidc_app
from orbitcloud_graviton.pulumi_lib import AzureBase, PulumiConfig, get_azure_stack, print_pulumi_esc_oidc_yaml


class LandingZoneConfig(PulumiConfig):
    cr: ContainerRegistryConfig
    vnet: VnetConfig


def deploy_landing_zone() -> None:
    config: LandingZoneConfig = LandingZoneConfig.model_validate({})
    stack: AzureBase = get_azure_stack()
    # Resource Group
    az_rg: resources.ResourceGroup = az_resource_group_from_config(config=config)
    pulumi.export("resource_group_name", az_rg.name)

    # Pulumi Deployments Entra App - OIDC
    esc_app, _, _ = deployment_oidc_app(
        workload_name=stack.workload_name,
        pulumi_org=pulumi.get_organization(),
        subscription_id=str(stack.subscription_id),
    )

    # Container Registry
    az_cr: containerregistry.Registry = az_containerregistry(
        workload_name=stack.workload_name,
        env=stack.env,
        location=stack.location,
        resource_group=az_rg,
        ip_allow_list=config.cr.ip_allow_list,
        public_network_access=config.cr.public_network_access,
        opts=pulumi.ResourceOptions(parent=az_rg),
    )
    pulumi.export("containerregistry_server", az_cr.login_server)
    pulumi.export("containerregistry_id", az_cr.id)

    # Keyvault
    az_kv: keyvault.Vault = az_keyvault(
        workload_name=stack.workload_name,
        env=stack.env,
        location=stack.location,
        resource_group=az_rg,
        tenant_id=str(stack.tenant_id),
        opts=pulumi.ResourceOptions(parent=az_rg),
    )
    pulumi.export("keyvault_name", az_kv.name)
    pulumi.export("keyvault_id", az_kv.id)

    pulumi.Output.all(esc_app.client_id, stack.tenant_id, stack.subscription_id).apply(func=print_pulumi_esc_oidc_yaml)

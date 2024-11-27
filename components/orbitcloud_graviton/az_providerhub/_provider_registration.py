import pulumi
from pulumi_azure_native.providerhub import v20210901preview as providerhub

from orbitcloud_graviton.pulumi_lib import AzureStack


def provider_registration(
    stack: AzureStack,
    provider_namespace: str,
    opts: pulumi.ResourceOptions | None = None,
):
    return providerhub.ProviderRegistration(
        resource_name=stack.name_for(
            providerhub.ProviderRegistration, workload_name=provider_namespace
        ),
        provider_namespace=provider_namespace,
        opts=opts,
    )

from orbitcloud_graviton.entra import ExternalIdTenant, ExternalIdTenantConfig
from orbitcloud_graviton.pulumi_lib import (
    AzureStack,
    EntraStack,
    PulumiConfig,
    generate_stack_schema,
    get_azure_stack,
    get_entra_stack,
)


class EntraExternalIdBaseConfig(PulumiConfig):
    tenant: ExternalIdTenantConfig


def deploy() -> None:
    generate_stack_schema(model=EntraExternalIdBaseConfig, output_file=".stack_schema.json")

    config: EntraExternalIdBaseConfig = EntraExternalIdBaseConfig.model_validate({})
    entra_config: EntraStack = EntraStack.model_validate({})

    # Get Azure Stack and export resource group
    stack: AzureStack = get_azure_stack()
    entra_config: EntraStack = get_entra_stack()

    ExternalIdTenant(
        stack=stack,
        entra_config=entra_config,
        config=config.tenant,
    )

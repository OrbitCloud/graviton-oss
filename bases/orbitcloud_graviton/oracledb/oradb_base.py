from orbitcloud_graviton.az_compute import VirtualMachineConfig
from orbitcloud_graviton.az_compute.vm import VirtualMachine
from orbitcloud_graviton.pulumi_lib import (
    AzureStack,
    EntraStack,
    PulumiConfig,
    generate_stack_schema,
    get_azure_stack,
    get_entra_stack,
)


class OracleDatabaseConfig(PulumiConfig):
    vm: VirtualMachineConfig


def deploy() -> None:
    generate_stack_schema(model=OracleDatabaseConfig, output_file=".stack_schema.json")

    config: OracleDatabaseConfig = OracleDatabaseConfig.model_validate({})
    entra_config: EntraStack = EntraStack.model_validate({})

    # Get Azure Stack and export resource group
    stack: AzureStack = get_azure_stack()
    entra_config: EntraStack = get_entra_stack()

    VirtualMachine(
        stack=stack,
        entra_config=entra_config,
        config=config.vm,
    )

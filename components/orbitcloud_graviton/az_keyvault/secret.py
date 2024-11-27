import pulumi
from pulumi_azure_native import keyvault
from pydantic import BaseModel, ConfigDict, SecretStr

from orbitcloud_graviton.az_lib.types import AzureIdRef
from orbitcloud_graviton.pulumi_lib.azure_base import AzureStack


class KeyvaultSecretConfig(BaseModel):
    name: str
    value: SecretStr | pulumi.Output[str]
    content_type: str | None = None
    keyvault_id: AzureIdRef

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


def keyvault_secret(
    stack: AzureStack,
    config: KeyvaultSecretConfig,
    opts: pulumi.ResourceOptions | None = None,
) -> keyvault.Secret:
    if isinstance(config.value, SecretStr):
        value = str(config.value.get_secret_value())
    if isinstance(config.value, pulumi.Output):
        value = config.value

    kv: keyvault.Vault = keyvault.Vault.get(resource_name="kv-ref", id=config.keyvault_id)

    return keyvault.Secret(
        resource_name=stack.name_for(resource_type=keyvault.Secret, workload_name=config.name),
        secret_name=config.name,
        vault_name=kv.name,
        resource_group_name=stack.resource_group.name,
        properties=keyvault.SecretPropertiesArgs(
            value=value,
            content_type=config.content_type,
        ),
        opts=opts,
    )

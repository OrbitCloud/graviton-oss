from typing import Optional, Union

import pulumi
from pulumi_azure_native import keyvault
from pydantic import BaseModel, ConfigDict, SecretStr

from orbitcloud_graviton.az_lib.types import AzureIdRef
from orbitcloud_graviton.pulumi_lib.azure_base import AzureBase


class KeyvaultSecretConfig(BaseModel):
    name: str
    value: Union[SecretStr, pulumi.Output[str]]
    content_type: Optional[str] = None
    keyvault_id: AzureIdRef

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


def keyvault_secret(
    stack: AzureBase,
    config: KeyvaultSecretConfig,
    opts: Optional[pulumi.ResourceOptions] = None,
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

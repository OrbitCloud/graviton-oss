from typing import Optional

import pulumi
from pulumi_azure_native import keyvault
from pydantic import BaseModel, ConfigDict, SecretStr

from orbitcloud_graviton.az_lib.types import AzureResourceId
from orbitcloud_graviton.pulumi_lib.azure_base import AzureBase


class SecretConfig(BaseModel):
    name: str
    value: SecretStr
    vault: AzureResourceId

    model_config = ConfigDict(arbitrary_types_allowed=True)


def key_vault_secret(
    stack: AzureBase,
    config: SecretConfig,
    opts: Optional[pulumi.ResourceOptions] = None,
) -> keyvault.Secret:
    return keyvault.Secret(
        resource_name=stack.name_for(resource_type=keyvault.Secret, workload_name=config.name),
        secret_name=config.name,
        vault_name=config.vault.resource_name,
        resource_group_name=config.vault.resource_group_name,
        properties=keyvault.SecretPropertiesArgs(
            value=config.value.get_secret_value(),
        ),
        opts=opts,
    )

from typing import Any, List, Literal, Optional, Union

import pulumi
from pulumi_azure_native.containerregistry import v20231101preview as containerregistry
from pydantic import BaseModel, ConfigDict, Field

from orbitcloud_graviton.az_lib.types import StrRef
from orbitcloud_graviton.az_network.types import PrivateIPv4Network, PublicIPv4Network
from orbitcloud_graviton.pulumi_lib import AzureStack


class ContainerRegistryConfig(BaseModel):
    name: Optional[str] = None
    public_network_access: containerregistry.PublicNetworkAccess = (
        containerregistry.PublicNetworkAccess.DISABLED
    )
    ip_allow_list: Optional[List[Union[PrivateIPv4Network, PublicIPv4Network, StrRef]]] = Field(
        default_factory=list
    )
    admin_user_enabled: Optional[bool] = False

    sku: Optional[Literal["Standard", "Premium"]] = Field(
        default="Premium",
        title="SKU",
        description="The SKU of the Container Registry. Default is Premium.",
        examples=["Standard", "Premium"],
    )

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


def container_registry(
    stack: AzureStack,
    config: ContainerRegistryConfig,
    opts: Optional[pulumi.ResourceOptions] = None,
) -> containerregistry.Registry:
    """Create container registry"""

    cr = containerregistry.Registry(
        resource_name=config.name if config.name else stack.name_for(containerregistry.Registry),
        registry_name=config.name if config.name else stack.name_for(containerregistry.Registry),
        admin_user_enabled=config.admin_user_enabled,
        location=stack.location,
        resource_group_name=stack.resource_group.name,
        network_rule_set=containerregistry.NetworkRuleSetArgs(
            default_action="Deny",
            # For all ip_allow_list, add ip address to network rules
            ip_rules=[
                containerregistry.IPRuleArgs(
                    action="Allow",
                    i_p_address_or_range=str(ip),
                )
                for ip in config.ip_allow_list
            ],
        )
        if config.ip_allow_list
        else None,
        sku=containerregistry.SkuArgs(
            name=config.sku if config.sku else "Premium",
        ),
        opts=opts,
    )

    admin_credentials: dict[str, pulumi.Output[Any]] | None = None
    if config.admin_user_enabled:
        try:
            creds = containerregistry.list_registry_credentials_output(
                resource_group_name=stack.resource_group.name,
                registry_name=cr.name,
            )
            admin_credentials = {
                "username": pulumi.Output.secret(creds.username),
                "password": pulumi.Output.secret(creds.passwords[0].value),
            }
        except Exception as e:
            pulumi.warn(f"Failed to get admin credentials: {e}")

    stack.export(
        exports={
            "container_registry": {
                "id": cr.id,
                "name": cr.name,
                "login_server": cr.login_server,
                "admin_user_enabled": config.admin_user_enabled,
                "admin_credentials": admin_credentials,
            },
        }
    )

    return cr

from dataclasses import dataclass, field
from typing import (
    List,
    Optional,
)
import pulumi
from pulumi_azure_native import resources, containerregistry
from orbitcloud_graviton.az_lib import BaseConfig
from orbitcloud_graviton.az_lib.config import StackConfig
from orbitcloud_graviton.az_resources import az_resource_group
from orbitcloud_graviton.az_acr import az_containerregistry


@dataclass
class LandingSiteConfig(BaseConfig):
    cr_ip_allow_list: Optional[List[str]] = field(default_factory=list)
    cr_public_network_access: Optional[str] = field(
        default=containerregistry.PublicNetworkAccess.DISABLED
    )


def deploy() -> None:
    config = StackConfig(LandingSiteConfig).get_config

    az_rg: resources.ResourceGroup = az_resource_group(
        workload_name=config.workload_name,
        env=config.env,
        location=config.location,
        tags=config.tags,
    )

    az_cr: containerregistry.Registry = az_containerregistry(
        workload_name=config.workload_name,
        env=config.env,
        location=config.location,
        resource_group=az_rg,
        ip_allow_list=config.cr_ip_allow_list,
        public_network_access=config.cr_public_network_access,
    )

    pulumi.export("resource_group_name", az_rg.name)
    pulumi.export("containerregistry_server", az_cr.login_server)

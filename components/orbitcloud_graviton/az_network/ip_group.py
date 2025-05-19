from ipaddress import IPv4Network

import pulumi
from pulumi_azure_native import network
from pydantic import BaseModel, ConfigDict

from orbitcloud_graviton.pulumi_lib import AzureStack


class IpGroupConfig(BaseModel):
    workload: str
    ip_addresses: IPv4Network | list[IPv4Network]

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


def ip_group(
    stack: AzureStack,
    config: IpGroupConfig,
    opts: pulumi.ResourceOptions | None = None,
) -> network.IpGroup:
    if isinstance(config.ip_addresses, list):
        ip_addresses = [str(ip) for ip in config.ip_addresses]
    else:
        ip_addresses = [str(config.ip_addresses)]

    return network.IpGroup(
        resource_name=f"ipg-{config.workload}",
        args=network.IpGroupArgs(
            resource_group_name=stack.resource_group.name,
            location=stack.location,
            ip_groups_name=f"ipg-{config.workload}",
            ip_addresses=ip_addresses,
        ),
        opts=opts,
    )

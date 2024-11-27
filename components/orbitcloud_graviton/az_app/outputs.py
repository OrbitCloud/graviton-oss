from ipaddress import IPv4Address

from pydantic import BaseModel, ConfigDict

from orbitcloud_graviton.az_lib.types import AzureResourceId
from orbitcloud_graviton.pulumi_lib.types import DomainName


class ContainerAppEnvOutput(BaseModel):
    id: AzureResourceId
    name: str
    static_ip: IPv4Address
    custom_domain_verification_id: str
    dns_suffix: DomainName | None = None
    certificates: dict | None = None

    @property
    def resource_group_name(self) -> str:
        if not self.id.resource_group_name:
            raise ValueError("Resource group name is not available")
        return self.id.resource_group_name

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

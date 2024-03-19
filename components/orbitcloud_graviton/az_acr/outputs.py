from pydantic import BaseModel, ConfigDict

from orbitcloud_graviton.az_lib.types import AzureResourceId
from orbitcloud_graviton.pulumi_lib.types import DomainName


class AdminUserEnabledRegistryOutput(BaseModel):
    id: AzureResourceId
    name: str
    login_server: DomainName
    admin_user_enabled: bool
    admin_credentials: dict[str, str]

    @property
    def resource_group_name(self) -> str:
        if not self.id.resource_group_name:
            raise ValueError("Resource group name is not available")
        return self.id.resource_group_name

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

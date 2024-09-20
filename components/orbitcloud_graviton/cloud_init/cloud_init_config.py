from typing import Optional

import pulumi
from pydantic import BaseModel, ConfigDict

from orbitcloud_graviton.az_lib.types import AzureIdRef, DictRef, StrRef


class CloudInitConfig(BaseModel):
    id_reference: AzureIdRef
    str_reference: StrRef
    dict_reference: DictRef

    log_workspace_id: Optional[AzureIdRef] = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class CloudInit:
    def __init__(
        self,
        config: CloudInitConfig,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        self.config: CloudInitConfig = config
        self.opts = opts

        self.config_file = self._config_file()

    def _config_file(self):
        pass

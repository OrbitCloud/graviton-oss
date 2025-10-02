from typing import Literal

import pulumi
from pulumi_azure_native import compute
from pydantic import BaseModel, ConfigDict, model_validator

from orbitcloud_graviton.az_lib.types import AzureIdRef
from orbitcloud_graviton.pulumi_lib import AzureStack


class VirtualMachineDiskConfig(BaseModel):
    size_gb: int
    create_mode: compute.DiskCreateOption = compute.DiskCreateOption.EMPTY
    sku: compute.DiskStorageAccountTypes | None = compute.DiskStorageAccountTypes.PREMIUM_V2_LRS
    caching: compute.CachingTypes | None = None
    source_disk_id: AzureIdRef | None = None
    source_image_id: AzureIdRef | None = None
    zone: str | None = None
    bursting_enabled: bool | None = False
    iops: int | None = 3000
    throughput_mbps: int | None = 125
    logical_sector_size: Literal[512, 4096] = 4096

    # Optional configurations (– v1 generation and windows is not supported yet)
    hyper_v_generation: compute.HyperVGeneration | None = compute.HyperVGeneration.V2
    os_type: compute.OperatingSystemTypes | None = compute.OperatingSystemTypes.LINUX

    @model_validator(mode="after")
    def validate_create_mode(m: "VirtualMachineDiskConfig") -> "VirtualMachineDiskConfig":
        if (
            m.create_mode == compute.DiskCreateOption.ATTACH
            or m.create_mode == compute.DiskCreateOption.COPY
        ) and not m.source_disk_id:
            raise ValueError("source_disk_id is required when create_mode is ATTACH")
        if m.create_mode == compute.DiskCreateOption.FROM_IMAGE and not m.source_image_id:
            raise ValueError("source_image_id is required when create_mode is COPY")

        return m

    @model_validator(mode="after")
    def validate_os_type(m: "VirtualMachineDiskConfig") -> "VirtualMachineDiskConfig":
        if m.os_type == compute.OperatingSystemTypes.WINDOWS:
            raise ValueError("Windows OS is not supported yet")

        if m.hyper_v_generation == compute.HyperVGeneration.V1:
            raise ValueError("Hyper-V Generation 1 is not (tested/supported yet)")

        return m

    log_workspace_id: AzureIdRef | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class VirtualMachineDataDiskConfig(VirtualMachineDiskConfig):
    lun: int
    name: str
    mount_point: str | None = None


class VirtualMachineDisk:
    def __init__(
        self,
        stack: AzureStack,
        config: VirtualMachineDiskConfig | VirtualMachineDataDiskConfig,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        self.stack: AzureStack = stack
        self.config: VirtualMachineDiskConfig = config

        self._opts: pulumi.ResourceOptions | None = opts

        self.disk: compute.Disk = self._disk()

        self._outputs()

    def _disk(self) -> compute.Disk:
        workload_name: str = self.stack.workload_name

        if isinstance(self.config, VirtualMachineDataDiskConfig):
            workload_name += f"-{self.config.name}"

        return compute.Disk(
            resource_name=self.stack.name_for(
                resource_type=compute.Disk,
                workload_name=workload_name,
            ),
            args=compute.DiskArgs(
                resource_group_name=self.stack.resource_group.name,
                disk_name=self.stack.name_for(
                    resource_type=compute.Disk,
                    workload_name=workload_name,
                ),
                disk_size_gb=self.config.size_gb,
                creation_data=compute.CreationDataArgs(
                    create_option=self.config.create_mode,
                    logical_sector_size=self.config.logical_sector_size,
                ),
                bursting_enabled=self.config.bursting_enabled,
                disk_m_bps_read_write=self.config.throughput_mbps,
                disk_iops_read_write=self.config.iops,
                sku=compute.DiskSkuArgs(
                    name=self.config.sku,
                ),
                zones=[self.config.zone] if self.config.zone else None,
            ),
            opts=self._opts,
        )

    def _outputs(self) -> None:
        self.stack.export(
            exports={
                "disk": {
                    "id": self.disk.id,
                    "name": self.disk.name,
                }
            }
        )

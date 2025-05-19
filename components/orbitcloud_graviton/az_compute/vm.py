import base64

import pulumi
from pulumi_azure_native import compute
from pydantic import Base64Str, BaseModel, ConfigDict, model_validator

from orbitcloud_graviton.az_lib.types import AzureIdRef
from orbitcloud_graviton.az_network import NetworkInterface, NetworkInterfaceConfig
from orbitcloud_graviton.pulumi_lib import AzureStack, EntraStack

from .disk import VirtualMachineDataDiskConfig, VirtualMachineDisk, VirtualMachineDiskConfig


class VirtualMachineOsImage(BaseModel):
    offer: str | None = None
    publisher: str | None = None
    sku: str | None = None
    version: str | None = "latest"
    gallery_urn: str | None = None
    is_marketplace_image: bool | None = False

    @model_validator(mode="after")
    def validate_urn(m: "VirtualMachineOsImage") -> "VirtualMachineOsImage":
        # Either offer, publisher, sku, and version or gallery_urn must be provided
        if not all([m.offer, m.publisher, m.sku]) and not m.gallery_urn:
            raise ValueError("Either offer, publisher and sku or gallery_urn must be provided")
        return m

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class VirtualMachineOsAdminUser(BaseModel):
    username: str | None = "azureuser"
    authorized_ssh_keys: list[str] | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class VirtualMachineOsConfig(BaseModel):
    image: VirtualMachineOsImage
    hostname: str | None = None
    disk: VirtualMachineDiskConfig
    admin: VirtualMachineOsAdminUser = VirtualMachineOsAdminUser()
    custom_data: Base64Str | pulumi.Output[str] | None = None
    custom_data_file: str | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class VirtualMachineNetworking(BaseModel):
    subnet_id: AzureIdRef

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class VirtualMachineConfig(BaseModel):
    os: VirtualMachineOsConfig
    networking: VirtualMachineNetworking
    storage: list[VirtualMachineDataDiskConfig] | None = None
    sku: str = compute.VirtualMachineSizeTypes.STANDARD_B2S
    zone: str | None = None

    log_workspace_id: AzureIdRef | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class VirtualMachine(pulumi.ComponentResource):
    def __init__(
        self,
        stack: AzureStack,
        entra_config: EntraStack,
        config: VirtualMachineConfig,
        nic: NetworkInterface | None = None,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        self.stack: AzureStack = stack
        self.config: VirtualMachineConfig = config
        self.entra_config: EntraStack = entra_config

        super().__init__(
            "Graviton:VirtualMachine",
            name=f"virtualmachine-{stack.workload_name}-{stack.env}",
            props=None,
            opts=opts,
        )

        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts1=opts, opts2=pulumi.ResourceOptions(parent=self)
        )

        self.datadisks: list[compute.DataDiskArgs] | None = self._datadisk_args()

        self.nic: NetworkInterface = (
            nic
            if nic
            else NetworkInterface(
                stack=stack,
                config=NetworkInterfaceConfig(
                    subnet_id=config.networking.subnet_id,
                ),
                opts=self._opts,
            )
        )

        self.vm: compute.VirtualMachine = self._vm()

        self._outputs()

    def _vm(self) -> compute.VirtualMachine:
        return compute.VirtualMachine(
            resource_name=self.stack.name_for(resource_type=compute.VirtualMachine),
            args=compute.VirtualMachineArgs(
                vm_name=self.stack.name_for(resource_type=compute.VirtualMachine),
                resource_group_name=self.stack.resource_group.name,
                location=self.stack.location,
                diagnostics_profile=compute.DiagnosticsProfileArgs(
                    boot_diagnostics=compute.BootDiagnosticsArgs(
                        enabled=True,
                    )
                ),
                hardware_profile=compute.HardwareProfileArgs(
                    vm_size=self.config.sku,
                ),
                os_profile=compute.OSProfileArgs(
                    admin_username=self.config.os.admin.username,
                    computer_name=self.config.os.hostname
                    or self.stack.name_for(resource_type=compute.VirtualMachine),
                    linux_configuration=compute.LinuxConfigurationArgs(
                        disable_password_authentication=True,
                        ssh=compute.SshConfigurationArgs(
                            public_keys=[
                                compute.SshPublicKeyArgs(
                                    path=f"/home/{self.config.os.admin.username}/.ssh/authorized_keys",
                                    key_data=key,
                                )
                                for key in self.config.os.admin.authorized_ssh_keys
                            ],
                        )
                        if self.config.os.admin.authorized_ssh_keys
                        else None,
                    ),
                    custom_data=self._custom_data(),
                ),
                identity=compute.VirtualMachineIdentityArgs(
                    type=compute.ResourceIdentityType.SYSTEM_ASSIGNED,
                ),
                network_profile=compute.NetworkProfileArgs(
                    network_interfaces=[
                        compute.NetworkInterfaceReferenceArgs(
                            id=self.nic.nic.id,
                            delete_option=compute.DeleteOptions.DETACH,
                        ),
                    ]
                ),
                plan=compute.PlanArgs(
                    publisher=self.config.os.image.publisher,
                    product=self.config.os.image.offer,
                    name=self.config.os.image.sku,
                )
                if self.config.os.image.is_marketplace_image
                else None,
                storage_profile=compute.StorageProfileArgs(
                    image_reference=compute.ImageReferenceArgs(
                        publisher=self.config.os.image.publisher,
                        offer=self.config.os.image.offer,
                        sku=self.config.os.image.sku,
                        version=self.config.os.image.version,
                        shared_gallery_image_id=self.config.os.image.gallery_urn,
                    )
                    if not self.config.os.image.is_marketplace_image
                    else None,
                    os_disk=compute.OSDiskArgs(
                        create_option=compute.DiskCreateOptionTypes.FROM_IMAGE,
                        delete_option=compute.DeleteOptions.DELETE,
                        disk_size_gb=self.config.os.disk.size_gb,
                        caching=compute.CachingTypes.READ_WRITE,
                        managed_disk=compute.ManagedDiskParametersArgs(
                            storage_account_type=compute.StorageAccountTypes.PREMIUM_LRS,
                        ),
                        name=f"osdisk-{self.stack.name_for(resource_type=compute.VirtualMachine)}",
                    ),
                    data_disks=self.datadisks,
                ),
                zones=[self.config.zone] if self.config.zone else None,
            ),
            opts=pulumi.ResourceOptions.merge(
                self._opts, pulumi.ResourceOptions(ignore_changes=["osProfile.customData"])
            ),
        )

    def _custom_data(self) -> Base64Str | pulumi.Output[Base64Str] | None:
        if self.config.os.custom_data:
            return self.config.os.custom_data

        if self.config.os.custom_data_file:
            with open(self.config.os.custom_data_file) as file:
                contents = file.read()
            return base64.b64encode(contents.encode("utf-8")).decode("utf-8")

    def _datadisk_args(self) -> list[compute.DataDiskArgs] | None:
        datadisks: list[compute.DataDiskArgs] = []
        for disk in self.config.storage or []:
            _disk = VirtualMachineDisk(
                stack=self.stack,
                config=disk.model_copy(update={"zone": self.config.zone}),
                opts=self._opts,
            )
            datadisks.append(
                compute.DataDiskArgs(
                    create_option=compute.DiskCreateOptionTypes.ATTACH,
                    lun=disk.lun,
                    caching=disk.caching,
                    managed_disk=compute.ManagedDiskParametersArgs(
                        id=_disk.disk.id,
                    ),
                )
            )
        return datadisks

    def _outputs(self) -> None:
        self.register_outputs(
            outputs={"vm": self.vm},
        )

        self.stack.export(
            exports={
                "vm": {
                    "id": self.vm.id,
                    "name": self.vm.name,
                    "username": self.config.os.admin.username,
                    "private_ip": self.nic.nic.ip_configurations[0].private_ip_address,
                }
            }
        )

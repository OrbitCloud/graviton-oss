import os
from base64 import b64decode

import pulumi
from pulumi_azure_native.storage import v20230501 as storage
from pulumi_cloudinit import Config
from pydantic import BaseModel, Field

from orbitcloud_graviton.az_compute import VirtualMachine, VirtualMachineConfig
from orbitcloud_graviton.az_storage import (
    StorageAccount,
    StorageAccountConfig,
    StorageAccountFileShareConfig,
)
from orbitcloud_graviton.cloud_init.template import CloudInitTemplate, ContentType
from orbitcloud_graviton.pulumi_lib import (
    AzureStack,
    EntraStack,
    PulumiConfig,
    generate_stack_schema,
    get_azure_stack,
    get_entra_stack,
)


class StorageAccountConfigOracleDefaults(StorageAccountConfig):
    sku: storage.SkuName = storage.SkuName.STANDARD_RAGRS
    smb_secure_defaults: bool = True
    file_shares: list[StorageAccountFileShareConfig] = Field(default=...)
    allow_shared_key_access: bool = True


class OracleDatabaseBackupConfig(BaseModel):
    storage: StorageAccountConfigOracleDefaults


class CloudInitConfig(BaseModel):
    mount_point_base: str = "/mnt"
    timezone: str = "UTC"


class OracleDatabaseInstanceConfig(BaseModel):
    oracle_home: str
    oracle_sid: str


class OracleDatabaseConfig(PulumiConfig):
    vm: VirtualMachineConfig
    backup: OracleDatabaseBackupConfig
    cloud_init: CloudInitConfig = CloudInitConfig()


def deploy() -> None:
    generate_stack_schema(model=OracleDatabaseConfig, output_file=".stack_schema.json")

    config: OracleDatabaseConfig = OracleDatabaseConfig.model_validate({})
    entra_config: EntraStack = EntraStack.model_validate({})

    # Get Azure Stack and export resource group
    stack: AzureStack = get_azure_stack()
    entra_config: EntraStack = get_entra_stack()

    opts = pulumi.ResourceOptions(parent=stack.resource_group)

    sa_backups = StorageAccount(
        stack=stack.model_copy(update={"workload_name": f"{stack.workload_name}-backup"}),
        config=config.backup.storage,
        opts=opts,
    )

    storage_account_key: pulumi.Output[str] = storage.list_storage_account_keys_output(
        account_name=sa_backups.storage_account.name,
        resource_group_name=stack.resource_group.name,
    ).apply(lambda keys: keys.keys[0].value)

    init = CloudInitTemplate()

    # Expand OS disk logical volume if needed
    init.add(tpl="azure/expand_lvm_osdisk.sh", content_type=ContentType.SHELL)

    # Set timezone
    init.add(tpl="linux/timezone.yaml.j2", timezone=config.cloud_init.timezone)

    # Set SELinux to permissive
    init.add(tpl="linux/selinux_permissive.yaml")

    # Setup hosts file for Oracle DB
    init.add(tpl="azure/hosts_file_privateip.yaml", content_type=ContentType.JINJA2)

    # Install Azure CLI
    init.add(tpl="azure/install_azcli.yaml")

    # Install Oracle DB dependencies
    init.add(tpl="oracledb/dependencies.yaml")

    # Setup data volumes
    init.add(
        tpl="azure/datadisk_lvm_setup.yaml.j2",
        volumes=[
            {
                "lun": disk.lun,
                "name": disk.name.replace("-", "_"),
                "mount_point": disk.mount_point
                if disk.mount_point
                else f"{config.cloud_init.mount_point_base}/{disk.name}",
            }
            for disk in config.vm.storage or []
        ],
    )

    # Configure Azure ephemeral disk
    init.add(tpl="azure/resource_disk.yaml")

    # Setup Storage Account File Shares
    init.add(
        tpl="azure/file_shares.yaml.j2",
        storage_account_name=sa_backups.storage_account.name,
        storage_account_key=storage_account_key,
        shares=[share.name for share in sa_backups.storage_shares.values()],
    )

    # Download Oracle DB 19c
    init.add(tpl="oracledb/19c_download.yaml")

    cloud_init_config = Config(
        resource_name="cloud-init-config",
        parts=init.parts,
        # base64_encode=False,
        gzip=False,
    )

    config.vm.os.custom_data = cloud_init_config.rendered
    cloud_init_config.rendered.apply(lambda content: print(b64decode(content).decode("utf-8")))

    if not os.getenv("DEL") == "TRUE":
        VirtualMachine(
            stack=stack,
            entra_config=entra_config,
            config=config.vm,
            opts=pulumi.ResourceOptions.merge(
                opts1=opts, opts2=pulumi.ResourceOptions(depends_on=[sa_backups, cloud_init_config])
            ),
        )

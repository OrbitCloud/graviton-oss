import pulumi

# from pulumi_azure_native import
# from pulumi_azure_native.recoveryservices import v20240401 as recoveryservices
from pulumi_azure_native.recoveryservices import v20240201 as recoveryservices

# from pulumi_azure_native import recoveryservices
from pydantic import BaseModel, ConfigDict

from orbitcloud_graviton.pulumi_lib import AzureStack, EntraStack


class BackupVaultConfig(BaseModel):
    public_network_access: recoveryservices.PublicNetworkAccess = (
        recoveryservices.PublicNetworkAccess.DISABLED
    )

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class BackupVault(pulumi.ComponentResource):
    def __init__(
        self,
        stack: AzureStack,
        entra_config: EntraStack,
        config: BackupVaultConfig,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        self.stack: AzureStack = stack
        self.config: BackupVaultConfig = config
        self.entra_config: EntraStack = entra_config

        super().__init__(
            "Graviton:BackupVault",
            name=f"backupvault-{stack.workload_name}-{stack.env}",
            props=None,
            opts=opts,
        )

        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts1=opts, opts2=pulumi.ResourceOptions(parent=self)
        )

        self.backupvault: recoveryservices.Vault = self._backupvault()
        # self.policy = self._policy()

        self._outputs()

    def _backupvault(self) -> recoveryservices.Vault:
        return recoveryservices.Vault(
            resource_name=self.stack.name_for(
                resource_type=recoveryservices.Vault,
                workload_name=self.stack.workload_name,
            ),
            args=recoveryservices.VaultArgs(
                resource_group_name=self.stack.resource_group.name,
                vault_name=self.stack.name_for(
                    resource_type=recoveryservices.Vault,
                    workload_name=self.stack.workload_name,
                ),
                location=self.stack.location,
                properties=recoveryservices.VaultPropertiesArgs(
                    public_network_access=self.config.public_network_access,
                    redundancy_settings=recoveryservices.VaultPropertiesRedundancySettingsArgs(
                        standard_tier_storage_redundancy=recoveryservices.StandardTierStorageRedundancy.ZONE_REDUNDANT,
                    ),
                ),
                identity=recoveryservices.IdentityDataArgs(
                    type=recoveryservices.ResourceIdentityType.SYSTEM_ASSIGNED,
                ),
                sku=recoveryservices.SkuArgs(
                    name=recoveryservices.SkuName.STANDARD,
                ),
            ),
            opts=self._opts,
        )

    def _policy(self) -> recoveryservices.ProtectionPolicy:
        return recoveryservices.ProtectionPolicy(
            resource_name=self.stack.name_for(
                resource_type=recoveryservices.ProtectionPolicy,
                workload_name=self.stack.workload_name,
            ),
            args=recoveryservices.ProtectionPolicyArgs(
                resource_group_name=self.stack.resource_group.name,
                location=self.stack.location,
                vault_name=self.backupvault.name,
                policy_name=self.stack.name_for(
                    resource_type=recoveryservices.ProtectionPolicy,
                    workload_name=self.stack.workload_name,
                ),
                properties=recoveryservices.AzureIaaSVMProtectionPolicyArgs(
                    backup_management_type=recoveryservices.BackupManagementType.AZURE_IAAS_VM,
                    policy_type=recoveryservices.IAASVMPolicyType.V2,
                    schedule_policy=recoveryservices.SimpleSchedulePolicyV2Args(
                        schedule_policy_type="SimpleSchedulePolicyV2",
                        schedule_run_frequency=recoveryservices.ScheduleRunType.DAILY,
                        daily_schedule=recoveryservices.DailyScheduleArgs(
                            schedule_run_times=["2021-09-01T00:00:00Z"],
                        ),
                    ),
                    retention_policy=recoveryservices.SimpleRetentionPolicyArgs(
                        retention_policy_type="LongTermRetentionPolicy",
                        retention_duration=recoveryservices.RetentionDurationArgs(
                            count=30,
                            duration_type=recoveryservices.RetentionDurationType.DAYS,
                        ),
                    ),
                ),
            ),
            opts=self._opts,
        )

    def _outputs(self) -> None:
        self.register_outputs(
            {"backupvault": self.backupvault},
        )

        self.stack.export(
            exports={
                "backupvault": {
                    "id": self.backupvault.id,
                    "name": self.backupvault.name,
                }
            }
        )

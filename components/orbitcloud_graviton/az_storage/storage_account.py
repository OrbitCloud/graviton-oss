from ipaddress import IPv4Address
from typing import Any, Literal

import pulumi
from pulumi_azure_native.storage import v20230501 as storage
from pydantic import BaseModel, ConfigDict

from orbitcloud_graviton.az_lib.types import AzureIdRef
from orbitcloud_graviton.az_network import PrivateEndpoint
from orbitcloud_graviton.az_network.private_endpoint import PrivateEndpointConfig
from orbitcloud_graviton.az_storage.iam_roles import StorageAccountAppPermissions
from orbitcloud_graviton.pulumi_lib import AzureStack


class StorageAccountRoutingConfig(BaseModel):
    routing_preference: storage.RoutingChoice | None = storage.RoutingChoice.MICROSOFT_ROUTING
    publish_microsoft_endpoints: bool | None = True
    publish_internet_endpoints: bool | None = False

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class StorageAccountPrivateEndpointConfig(BaseModel):
    sub_types: list[Literal["blob", "file", "queue", "table"]]
    subnet_id: AzureIdRef
    private_dns_zone_id: AzureIdRef

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class StorageAccountFileShareConfig(BaseModel):
    name: str
    share_quota: int | None = 102400
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class StorageAccountCustomDomainConfig(BaseModel):
    name: str
    use_subdomain: bool | None = False
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class SftpSshKeyConfig(BaseModel):
    description: str | None
    key: str


class SftpContainerPermissions(BaseModel):
    container_name: str
    permissions: list[Literal["l", "r", "w", "d", "c"]]


class SftpUserConfig(BaseModel):
    username: str
    password_auth: bool = True
    home_directory: str = "/"
    containers: list[SftpContainerPermissions]
    ssh_keys: list[SftpSshKeyConfig] | None = None


class StorageAccountConfig(BaseModel):
    name: str | None = None
    kind: storage.Kind = storage.Kind.STORAGE_V2
    sku: storage.SkuName = storage.SkuName.PREMIUM_LRS
    tier: storage.AccessTier = storage.AccessTier.HOT

    allow_blob_public_access: bool | None = False
    allow_shared_key_access: bool | None = False
    public_network_access: storage.PublicNetworkAccess | None = storage.PublicNetworkAccess.DISABLED
    azure_portal_use_oauth: bool | None = True

    # File share options
    smb_secure_defaults: bool | None = True
    nfs_v3: bool | None = False
    large_file_shares: storage.LargeFileSharesState | None = storage.LargeFileSharesState.ENABLED
    hierarchical_namespace: bool | None = False

    # SFTP options
    sftp_enabled: bool | None = False
    sftp_users: list[SftpUserConfig] | None = None

    # Networking
    allowed_private_subnets: list[AzureIdRef] | None = None
    allowed_public_ips: list[IPv4Address] | None = None
    routing: StorageAccountRoutingConfig = StorageAccountRoutingConfig()
    private_endpoints: list[StorageAccountPrivateEndpointConfig] | None = None
    custom_domain: StorageAccountCustomDomainConfig | None = None

    storage_containers: list[str] | None = None
    storage_tables: list[str] | None = None
    storage_queues: list[str] | None = None
    file_shares: list[StorageAccountFileShareConfig] | None = None

    app_permissions: StorageAccountAppPermissions | None = None

    exports_prefix: str | None = None
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class StorageAccount(pulumi.ComponentResource):
    def __init__(
        self,
        stack: AzureStack,
        config: StorageAccountConfig,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        self.config: StorageAccountConfig = config
        self.stack: AzureStack = stack

        super().__init__(
            "Graviton:az_storage:StorageAccount",
            name=f"st-{self.stack.workload_name}",
            props=None,
            opts=opts,
        )
        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts1=opts, opts2=pulumi.ResourceOptions(parent=self)
        )

        self.name: str = self.stack.name_for(
            resource_type=storage.StorageAccount, workload_name=self.config.name
        )

        self.storage_account: storage.StorageAccount = self._storage_account()
        self.storage_container: list[storage.BlobContainer] = self._storage_containers()
        self.storage_tables: list[storage.Table] = self._storage_tables()
        self.storage_queues: list[storage.Queue] = self._storage_queues()
        self.storage_shares: dict[str, storage.FileShare] = self._storage_file_shares()

        self.sftp_users: list[storage.LocalUser] = self._sftp_users()

        self.private_endpoints: list[PrivateEndpoint] = self._private_endpoints()

        self._outputs()

    def _storage_account(self) -> storage.StorageAccount:
        return storage.StorageAccount(
            resource_name=self.name,
            args=storage.StorageAccountArgs(
                account_name=self.config.name,
                location=self.stack.location,
                resource_group_name=self.stack.resource_group.name,
                # Storage Account type
                kind=self.config.kind,
                sku=storage.SkuArgs(name=str(self.config.sku.value)),
                access_tier=self.config.tier,
                # Access management
                allow_shared_key_access=self.config.allow_shared_key_access,
                default_to_o_auth_authentication=self.config.azure_portal_use_oauth,
                # Network Access
                public_network_access=self.config.public_network_access,
                allow_blob_public_access=self.config.allow_blob_public_access,
                network_rule_set=self._network_rules(),
                routing_preference=storage.RoutingPreferenceArgs(
                    routing_choice=self.config.routing.routing_preference,
                    publish_microsoft_endpoints=self.config.routing.publish_microsoft_endpoints,
                    publish_internet_endpoints=self.config.routing.publish_internet_endpoints,
                ),
                custom_domain=storage.CustomDomainArgs(
                    name=self.config.custom_domain.name,
                    use_sub_domain_name=self.config.custom_domain.use_subdomain,
                )
                if self.config.custom_domain
                else None,
                # Protocols
                minimum_tls_version=storage.MinimumTlsVersion.TLS1_2,
                enable_nfs_v3=self.config.nfs_v3,
                large_file_shares_state=self.config.large_file_shares,
                is_sftp_enabled=self.config.sftp_enabled,
                is_hns_enabled=self.config.hierarchical_namespace,
            ),
            opts=self._opts,
        )

    def _network_rules(self) -> storage.NetworkRuleSetArgs | None:
        ip_rules = []
        vnet_rules = []

        if (self.config.public_network_access == storage.PublicNetworkAccess.DISABLED) and (
            self.config.allowed_public_ips or self.config.allowed_private_subnets
        ):
            pulumi.warn(
                msg="Public / private network ACL cannot be configured when Public Network Access is disabled."
            )
            return None

        if self.config.allowed_public_ips:
            ip_rules: list[storage.IPRuleArgs] = [
                storage.IPRuleArgs(i_p_address_or_range=str(object=public_ip))
                for public_ip in self.config.allowed_public_ips
            ]

        if self.config.allowed_private_subnets:
            vnet_rules: list[storage.VirtualNetworkRuleArgs] = []

            for subnet_id in self.config.allowed_private_subnets:
                vnet_rules.append(
                    storage.VirtualNetworkRuleArgs(virtual_network_resource_id=subnet_id)
                )

        return storage.NetworkRuleSetArgs(
            bypass="None",
            default_action=storage.DefaultAction.DENY,
            ip_rules=ip_rules,
            virtual_network_rules=vnet_rules,
        )

    def _private_endpoints(self) -> list[PrivateEndpoint]:
        sub_type_resources = {
            "blob": storage.BlobContainer,
            "file": storage.FileShare,
            "queue": storage.Queue,
            "table": storage.Table,
        }
        endpoints: list[PrivateEndpoint] = []
        if self.config.private_endpoints:
            for endpoint in self.config.private_endpoints:
                for sub_type in endpoint.sub_types:
                    endpoints.append(
                        PrivateEndpoint(
                            stack=self.stack,
                            target_resource=sub_type_resources[sub_type],
                            target_resource_name=self.name,
                            config=PrivateEndpointConfig(
                                subnet_id=endpoint.subnet_id,
                                private_dns_zone_id=endpoint.private_dns_zone_id,
                            ),
                            opts=self._opts,
                        )
                    )
        return endpoints

    def _storage_containers(self) -> list[storage.BlobContainer]:
        return (
            (
                [
                    storage.BlobContainer(
                        resource_name=self.stack.name_for(
                            resource_type=storage.BlobContainer, workload_name=container
                        ),
                        args=storage.BlobContainerArgs(
                            container_name=container,
                            account_name=self.storage_account.name,
                            resource_group_name=self.stack.resource_group.name,
                        ),
                        opts=self._opts._merge_instance(
                            opts=pulumi.ResourceOptions(parent=self.storage_account)
                        ),
                    )
                    for container in self.config.storage_containers
                ]
            )
            if self.config.storage_containers
            else []
        )

    def _storage_tables(self) -> list[storage.Table]:
        return (
            (
                [
                    storage.Table(
                        resource_name=self.stack.name_for(
                            resource_type=storage.Table, workload_name=table
                        ),
                        table_name=table,
                        account_name=self.storage_account.name,
                        resource_group_name=self.stack.resource_group.name,
                        signed_identifiers=[],
                        opts=self._opts._merge_instance(
                            opts=pulumi.ResourceOptions(parent=self.storage_account)
                        ),
                    )
                    for table in self.config.storage_tables
                ]
            )
            if self.config.storage_tables
            else []
        )

    def _storage_queues(self) -> list[storage.Queue]:
        return (
            [
                (
                    storage.Queue(
                        resource_name=self.stack.name_for(
                            resource_type=storage.Queue, workload_name=queue
                        ),
                        queue_name=queue,
                        account_name=self.storage_account.name,
                        resource_group_name=self.stack.resource_group.name,
                        opts=self._opts._merge_instance(
                            opts=pulumi.ResourceOptions(parent=self.storage_account)
                        ),
                    )
                )
                for queue in self.config.storage_queues
            ]
            if self.config.storage_queues
            else []
        )

    def _storage_file_shares(self) -> dict[str, storage.FileShare]:
        if self.config.file_shares and self.config.smb_secure_defaults:
            self._storage_file_share_security()

        _shares: dict[str, storage.FileShare] = {}

        for share in self.config.file_shares or []:
            _shares[share.name] = storage.FileShare(
                resource_name=self.stack.name_for(
                    resource_type=storage.FileShare, workload_name=share.name
                ),
                args=storage.FileShareArgs(
                    share_name=share.name,
                    account_name=self.storage_account.name,
                    resource_group_name=self.stack.resource_group.name,
                    share_quota=share.share_quota,
                ),
                opts=self._opts._merge_instance(
                    opts=pulumi.ResourceOptions(parent=self.storage_account)
                ),
            )
        return _shares

    def _storage_file_share_security(self) -> storage.FileServiceProperties | None:
        return storage.FileServiceProperties(
            resource_name=self.stack.name_for(resource_type=storage.FileServiceProperties),
            args=storage.FileServicePropertiesArgs(
                resource_group_name=self.stack.resource_group.name,
                account_name=self.storage_account.name,
                file_services_name="default",
                protocol_settings=storage.ProtocolSettingsArgs(
                    smb=storage.SmbSettingArgs(
                        # Note: Currently Azure doesn't support Kerberos AD authentication for SMB mounts
                        authentication_methods="NTLMv2;Kerberos;",
                        # cifs-utils version installed by most Linux distros don't support AES-256-GCM yet
                        # so also enable AES-128-GCM
                        channel_encryption="AES-256-GCM;AES-128-GCM;",
                        kerberos_ticket_encryption="AES-256;",
                        # Enforce the use of SMB3.1.1
                        # Encryption is enabled by default in SMB3.1.1
                        versions="SMB3.1.1;",
                    ),
                ),
                share_delete_retention_policy=storage.DeleteRetentionPolicyArgs(
                    days=30, enabled=True
                ),
            ),
            opts=self._opts,
        )

    def _sftp_users(self) -> list[storage.LocalUser]:
        users = []
        existing_containers: set[str] = set(self.config.storage_containers or [])

        if self.config.sftp_users:
            for user in self.config.sftp_users:
                for container_permission in user.containers:
                    container_name = container_permission.container_name

                    # Check if the container exists
                    if container_name not in existing_containers:
                        raise ValueError(
                            f"Container '{container_name}' does not exist for user '{user.username}'. Container name must be speficied in 'storage_containers' config."
                        )

                    permission_scopes = [
                        storage.PermissionScopeArgs(
                            permissions="".join(container_permission.permissions),
                            service="blob",
                            resource_name=container_name,
                        )
                    ]

                    sftp_user = storage.LocalUser(
                        resource_name=f"sftp-{container_name}-{user.username}",
                        args=storage.LocalUserArgs(
                            account_name=self.storage_account.name,
                            username=user.username,
                            resource_group_name=self.stack.resource_group.name,
                            home_directory=user.home_directory,
                            has_ssh_password=user.password_auth,
                            permission_scopes=permission_scopes,
                            ssh_authorized_keys=[
                                storage.SshPublicKeyArgs(key=key.key, description=key.description)
                                for key in user.ssh_keys or []
                            ],
                        ),
                        opts=self._opts._merge_instance(
                            opts=pulumi.ResourceOptions(
                                parent=self.storage_account, depends_on=self.storage_container
                            )
                        ),
                    )
                    users.append(sftp_user)
        return users

    def get_endpoints(
        self, suffix: str | None = None
    ) -> pulumi.Output[dict[str, Any]] | dict[str, pulumi.Output[Any]]:
        if (
            self.config.routing.routing_preference is storage.RoutingChoice.MICROSOFT_ROUTING
            and self.config.routing.publish_microsoft_endpoints
        ):
            endpoints: pulumi.Output[Any] = (
                self.storage_account.primary_endpoints.microsoft_endpoints
            )
        else:
            endpoints = self.storage_account.primary_endpoints

        # Endpoint availability depends on the SKU
        # see: https://learn.microsoft.com/en-us/azure/storage/common/storage-account-overview#types-of-storage-accounts

        active_endpoints = {}
        if endpoints.blob:
            active_endpoints.update({f'blob{"-" + suffix if suffix else ""}': endpoints.blob})

        if self.config.sku.startswith("STANDARD") and endpoints.file:
            active_endpoints.update({f'tables{"-" + suffix if suffix else ""}': endpoints.table})

        if (
            self.config.sku.startswith("STANDARD") or self.config.kind == storage.Kind.FILE_STORAGE
        ) and endpoints.file:
            active_endpoints.update({f'file{"-" + suffix if suffix else ""}': endpoints.file})

        if self.config.sku.startswith("STANDARD") and endpoints.queue:
            active_endpoints.update({f'queue{"-" + suffix if suffix else ""}': endpoints.queue})

        return active_endpoints

    def get_private_endpoints(self) -> dict[pulumi.Output[str], dict[str, Any]] | None:
        if self.private_endpoints:
            return {
                endpoint.private_endpoint.type: {
                    "name": endpoint.name,
                    "fqdn": endpoint.private_endpoint.custom_dns_configs.fqdn,
                    "ip": endpoint.private_endpoint.custom_dns_configs.ip_addresses,
                }
                for endpoint in self.private_endpoints
            }

    def _outputs(self) -> None:
        self.register_outputs(
            outputs={
                "storage_account": self.storage_account,
                "private_endpoints": self.private_endpoints,
            }
        )

        self.stack.export(
            exports={
                "storage_account": {
                    "name": self.storage_account.name,
                    "id": self.storage_account.id,
                    "endpoints": self.get_endpoints(),
                    "private_endpoints": self.get_private_endpoints(),
                },
            },
            prefix=self.config.exports_prefix,
        )

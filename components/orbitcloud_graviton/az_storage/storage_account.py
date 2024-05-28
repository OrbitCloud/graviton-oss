from ipaddress import IPv4Address
from typing import Any, Dict, List, Literal, Optional

import pulumi
from pulumi_azure_native.storage import v20230501 as storage
from pydantic import BaseModel, ConfigDict

from orbitcloud_graviton.az_lib.types import AzureIdRef
from orbitcloud_graviton.az_network import PrivateEndpoint
from orbitcloud_graviton.az_network.private_endpoint import PrivateEndpointConfig
from orbitcloud_graviton.az_storage.iam_roles import StorageAccountAppPermissions
from orbitcloud_graviton.pulumi_lib import AzureStack


class StorageAccountRoutingConfig(BaseModel):
    routing_preference: Optional[storage.RoutingChoice] = storage.RoutingChoice.MICROSOFT_ROUTING
    publish_microsoft_endpoints: Optional[bool] = True
    publish_internet_endpoints: Optional[bool] = False

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class StorageAccountPrivateEndpointConfig(BaseModel):
    sub_types: List[Literal["blob", "file", "queue", "table"]]
    subnet_id: AzureIdRef
    private_dns_zone_id: AzureIdRef

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class StorageAccountConfig(BaseModel):
    name: Optional[str] = None
    kind: storage.Kind = storage.Kind.STORAGE_V2
    sku: storage.SkuName = storage.SkuName.PREMIUM_LRS
    tier: storage.AccessTier = storage.AccessTier.HOT

    allow_blob_public_access: Optional[bool] = False
    allow_shared_key_access: Optional[bool] = False
    public_network_access: Optional[storage.PublicNetworkAccess] = (
        storage.PublicNetworkAccess.DISABLED
    )
    azure_portal_use_oauth: Optional[bool] = True

    nfs_v3: Optional[bool] = False

    allowed_private_subnets: Optional[List[AzureIdRef]] = None
    allowed_public_ips: Optional[List[IPv4Address]] = None
    routing: StorageAccountRoutingConfig = StorageAccountRoutingConfig()

    private_endpoints: Optional[list[StorageAccountPrivateEndpointConfig]] = None
    storage_containers: Optional[List[str]] = None
    storage_tables: Optional[List[str]] = None
    storage_queues: Optional[List[str]] = None

    app_permissions: Optional[StorageAccountAppPermissions] = None

    exports_prefix: Optional[str] = None
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class StorageAccount(pulumi.ComponentResource):
    def __init__(
        self,
        stack: AzureStack,
        config: StorageAccountConfig,
        opts: Optional[pulumi.ResourceOptions] = None,
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
        self.storage_container: List[storage.BlobContainer] = self._storage_containers()
        self.storage_tables: List[storage.Table] = self._storage_tables()
        self.storage_queues: List[storage.Queue] = self._storage_queues()

        self.private_endpoints: List[PrivateEndpoint] = self._private_endpoints()

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
                # Protocols
                minimum_tls_version=storage.MinimumTlsVersion.TLS1_2,
                enable_nfs_v3=self.config.nfs_v3,
            ),
            opts=self._opts,
        )

    def _network_rules(self) -> storage.NetworkRuleSetArgs | None:
        ip_rules = []
        vnet_rules = []

        if self.config.public_network_access == storage.PublicNetworkAccess.DISABLED:
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

    def _storage_containers(self) -> List[storage.BlobContainer]:
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

    def _storage_tables(self) -> List[storage.Table]:
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

    def _storage_queues(self) -> List[storage.Queue]:
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

    def get_endpoints(
        self, suffix: str | None = None
    ) -> pulumi.Output[Dict[str, Any]] | dict[str, pulumi.Output[Any]]:
        if (
            self.config.routing.routing_preference is storage.RoutingChoice.MICROSOFT_ROUTING
            and self.config.routing.publish_microsoft_endpoints
        ):
            endpoints: pulumi.Output[Any] = (
                self.storage_account.primary_endpoints.microsoft_endpoints
            )
        else:
            endpoints = self.storage_account.primary_endpoints

        return {
            f'tables{"-" + suffix if suffix else ""}': endpoints.table,
            f'blob{"-" + suffix if suffix else ""}': endpoints.blob,
            f'file{"-" + suffix if suffix else ""}': endpoints.file,
            f'queue{"-" + suffix if suffix else ""}': endpoints.queue,
        }

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

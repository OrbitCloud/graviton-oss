from ipaddress import IPv4Address
from typing import List, Optional

import pulumi
from pulumi_azure_native import storage
from pulumi_azure_native.network import v20230901 as network
from pydantic import BaseModel, ConfigDict

from orbitcloud_graviton.az_lib.types import AzureIdRef
from orbitcloud_graviton.az_network import (
    PrivateEndpointConfig,
    az_private_endpoint,
)
from orbitcloud_graviton.pulumi_lib import AzureBase


class StorageAccountConfig(BaseModel):
    name: Optional[str] = None
    kind: storage.Kind = storage.Kind.STORAGE_V2
    sku: storage.SkuName = storage.SkuName.STANDARD_LRS
    tier: storage.AccessTier = storage.AccessTier.HOT

    allow_blob_public_access: Optional[bool] = False
    allow_shared_key_access: Optional[bool] = False
    public_network_access: Optional[
        storage.PublicNetworkAccess
    ] = storage.PublicNetworkAccess.DISABLED

    nfs_v3: Optional[bool] = False

    allowed_private_subnets: Optional[List[AzureIdRef]] = None
    allowed_public_ips: Optional[List[IPv4Address]] = None

    private_endpoints: Optional[list[PrivateEndpointConfig]] = None
    storage_tables: Optional[List[str]] = None

    exports_prefix: Optional[str] = None
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class StorageAccount(pulumi.ComponentResource):
    def __init__(
        self,
        stack: AzureBase,
        config: StorageAccountConfig,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        self.config: StorageAccountConfig = config
        self.stack: AzureBase = stack

        super().__init__(
            "Graviton:az_storage:StorageAccount",
            name=f"st-{self.stack.workload_name}",
            props=None,
            opts=opts,
        )
        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts, pulumi.ResourceOptions(parent=self)
        )

        self.storage_account: storage.StorageAccount = self._storage_account()
        self.private_endpoints: Optional[list[network.PrivateEndpoint]] = self._private_endpoints()
        self.storage_tables: list[storage.Table] | None = self._storage_tables()

        self._outputs()

    def _storage_account(self) -> storage.StorageAccount:
        return storage.StorageAccount(
            resource_name=self.stack.name_for(
                storage.StorageAccount, workload_name=self.config.name
            ),
            account_name=self.stack.name_for(
                storage.StorageAccount, workload_name=self.config.name
            ),
            location=self.stack.location,
            resource_group_name=self.stack.resource_group.name,
            # Storage Account type
            kind=self.config.kind,
            sku=storage.SkuArgs(name=str(self.config.sku.value)),
            access_tier=self.config.tier,
            # Network Access
            public_network_access=self.config.public_network_access,
            allow_blob_public_access=self.config.allow_blob_public_access,
            allow_shared_key_access=self.config.allow_shared_key_access,
            network_rule_set=self._network_rules(),
            # Protocols
            minimum_tls_version=storage.MinimumTlsVersion.TLS1_2,
            enable_nfs_v3=self.config.nfs_v3,
            opts=self._opts,
        )

    def _network_rules(self) -> storage.NetworkRuleSetArgs | None:
        ip_rules = []
        vnet_rules = []

        if self.config.public_network_access == storage.PublicNetworkAccess.DISABLED:
            pulumi.warn(
                "Public / private network ACL cannot be configured when Public Network Access is disabled."
            )
            return None

        if self.config.allowed_public_ips:
            ip_rules: list[storage.IPRuleArgs] = [
                storage.IPRuleArgs(i_p_address_or_range=str(public_ip))
                for public_ip in self.config.allowed_public_ips
            ]

        if self.config.allowed_private_subnets:
            vnet_rules: list[storage.VirtualNetworkRuleArgs] = []

            for subnet_id in self.config.allowed_private_subnets:
                print(subnet_id)
                vnet_rules.append(
                    storage.VirtualNetworkRuleArgs(virtual_network_resource_id=subnet_id)
                )

        return storage.NetworkRuleSetArgs(
            bypass="None",
            default_action=storage.DefaultAction.DENY,
            ip_rules=ip_rules,
            virtual_network_rules=vnet_rules,
        )

    def _private_endpoints(self) -> list[network.PrivateEndpoint] | None:
        endpoints: list[network.PrivateEndpoint] = []
        if self.config.private_endpoints:
            for endpoint in self.config.private_endpoints:
                endpoints.append(
                    az_private_endpoint(
                        resource=self.storage_account,
                        resource_group=self.stack.resource_group,
                        private_endpoint_config=endpoint,
                        tags=self.stack.tags,
                        opts=self._opts,
                    )
                )
            return endpoints

    def _storage_tables(self) -> list[storage.Table] | None:
        return (
            (
                [
                    storage.Table(
                        resource_name=self.stack.name_for(storage.Table, table),
                        table_name=table,
                        account_name=self.storage_account.name,
                        resource_group_name=self.stack.resource_group.name,
                        signed_identifiers=[],
                        opts=self._opts._merge_instance(
                            pulumi.ResourceOptions(parent=self.storage_account)
                        ),
                    )
                    for table in self.config.storage_tables
                ]
            )
            if self.config.storage_tables
            else None
        )

    def _outputs(self) -> None:
        self.register_outputs(
            {
                "storage_account": self.storage_account,
                "private_endpoints": self.private_endpoints,
            }
        )

        pep_export = (
            [
                {
                    "id": endpoint.id,
                    "name": endpoint.name,
                    "fqdn": endpoint.custom_dns_configs.fqdn,
                    "ip": endpoint.custom_dns_configs.ip_addresses,
                }
                for endpoint in self.private_endpoints
            ]
            if self.private_endpoints
            else []
        )
        self.stack.export(
            exports={
                "storage_account": {
                    "name": self.storage_account.name,
                    "id": self.storage_account.id,
                    "tables_endpoint": self.storage_account.primary_endpoints.table,
                    "blob_endpoint": self.storage_account.primary_endpoints.blob,
                    "file_endpoint": self.storage_account.primary_endpoints.file,
                    "queue_endpoint": self.storage_account.primary_endpoints.queue,
                    "private_endpoints": pep_export,
                },
            },
            prefix=self.config.exports_prefix,
        )

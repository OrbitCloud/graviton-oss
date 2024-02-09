from typing import List, Optional, Union

import pulumi
from pulumi_azure_native import storage
from pulumi_azure_native.network import v20230201 as network
from pydantic import BaseModel, ConfigDict

from orbitcloud_graviton.az_lib.types import AzureResourceId
from orbitcloud_graviton.az_network import (
    PrivateEndpointConfig,
    PrivateIPv4Network,
    az_private_endpoint,
)
from orbitcloud_graviton.pulumi_lib import AzureBase


class StorageAccountConfig(BaseModel):
    kind: storage.Kind = storage.Kind.STORAGE_V2
    sku: storage.SkuName = storage.SkuName.STANDARD_LRS
    tier: storage.AccessTier = storage.AccessTier.HOT

    allow_blob_public_access: Optional[bool] = False
    allow_shared_key_access: Optional[bool] = False
    public_network_access: Optional[
        storage.PublicNetworkAccess
    ] = storage.PublicNetworkAccess.DISABLED

    nfs_v3: Optional[bool] = False

    allowed_private_subnets: Optional[List[Union[str, AzureResourceId]]] = None
    allowed_public_networks: Optional[List[PrivateIPv4Network]] = None

    private_endpoints: Optional[list[PrivateEndpointConfig]] = None
    storage_tables: Optional[List[str]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


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
            resource_name=self.stack.name_for(storage.StorageAccount),
            account_name=self.stack.name_for(storage.StorageAccount),
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

    def _network_rules(self):
        ip_rules = []
        vnet_rules = []

        if self.config.allowed_public_networks:
            ip_rules: list[storage.IPRuleArgs] = [
                storage.IPRuleArgs(i_p_address_or_range=str(ip_network))
                for ip_network in self.config.allowed_public_networks
            ]

        if self.config.allowed_private_subnets:
            vnet_rules: list[storage.VirtualNetworkRuleArgs] = []

            for subnet in self.config.allowed_private_subnets:
                subnet_id = subnet if isinstance(subnet, str) else subnet.id
                vnet_rules.append(
                    storage.VirtualNetworkRuleArgs(virtual_network_resource_id=subnet_id)
                )

        if (
            ip_rules or vnet_rules
        ) and self.config.public_network_access == storage.PublicNetworkAccess.ENABLED:
            pulumi.warn(
                "Public network access is enabled, but network rules are also set and will be ignored."
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
                        opts=self._opts,
                    )
                    for table in self.config.storage_tables
                ]
            )
            if self.config.storage_tables
            else None
        )

    def _outputs(self):
        self.register_outputs(
            {
                "storage_account": self.storage_account,
                "private_endpoints": self.private_endpoints,
            }
        )
        pulumi.export("storage_account_name", self.storage_account.name.apply(lambda x: x))
        pulumi.export("storage_account_id", self.storage_account.id)

        if self.private_endpoints:
            pulumi.export("private_endpoints", [endpoint.id for endpoint in self.private_endpoints])

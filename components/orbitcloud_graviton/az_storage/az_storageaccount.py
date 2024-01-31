from dataclasses import dataclass
from typing import Dict, List, Optional

import pulumi
from pulumi_azure_native import resources
from pulumi_azure_native.storage import v20220901 as storage

from orbitcloud_graviton.az_lib import Confy, StackConfig, is_public_ip, resource_namer
from orbitcloud_graviton.az_network import PrivateEndpointConfig, az_private_endpoint
from orbitcloud_graviton.az_resources import az_resource_group_from_config


def az_storageaccount(
    workload_name: str,
    env: str,
    location: str,
    resource_group: resources.ResourceGroup | resources.AwaitableGetResourceGroupResult,
    kind: Optional[str] = "StorageV2",
    sku: str = "Standard_LRS",
    minimum_tls_version: Optional[str] = "TLS1_2",
    allow_blob_public_access: Optional[bool] = False,
    allow_shared_key_access: Optional[bool] = False,
    enable_https_traffic_only: Optional[bool] = True,
    nfs_v3: Optional[bool] = False,
    use_managed_identity: Optional[bool] = True,
    virtual_network_subnets: Optional[List[str]] = None,
    public_network_access: Optional[str] = "Disabled",
    is_hns_enabled: Optional[bool] = False,
    access_tier: str = "Hot",
    network_rules: Optional[list] = None,
    private_endpoints: Optional[list[PrivateEndpointConfig]] = None,
    tags: Optional[Dict[str, str]] = None,
) -> storage.StorageAccount:
    storageacount_name: str = resource_namer(
        resource_type=storage.StorageAccount,
        workload_name=workload_name,
        env=env,
        location=location,
    )

    # Simple mapping from string to storage.AccessTier
    access_tier_map: dict[str, storage.AccessTier] = {
        "hot": storage.AccessTier.HOT,
        "cold": storage.AccessTier.COOL,
        "premium": storage.AccessTier.PREMIUM,
    }
    access_tier_enum = access_tier_map.get(access_tier.lower(), storage.AccessTier.HOT)

    # Initialize network_rule_set_args to None
    network_rule_set_args = None

    # Check if public network access is enabled and we have valid network rules
    if public_network_access != "Disabled":
        ip_rules = []
        vnet_rules = []

        # Validate and add public IP rules
        if network_rules is not None:
            for ip_rule in network_rules:
                try:
                    if is_public_ip(ip_rule):
                        ip_rules.append(storage.IPRuleArgs(i_p_address_or_range=ip_rule))
                    else:
                        pulumi.warn(f"The IP address or range {ip_rule} is private and will not be added.")
                except ValueError as e:
                    pulumi.warn(str(e))

        # Add virtual network rules
        if virtual_network_subnets is not None:
            vnet_rules = [
                storage.VirtualNetworkRuleArgs(virtual_network_resource_id=subnet_id)
                for subnet_id in virtual_network_subnets
            ]

        # Combine IP rules and VNet rules if any are defined
        if ip_rules or vnet_rules:
            network_rule_set_args = storage.NetworkRuleSetArgs(
                bypass="None",
                default_action=storage.DefaultAction.DENY,
                ip_rules=ip_rules,
                virtual_network_rules=vnet_rules,
            )
    else:
        # Only warn if the user has provided network rules or subnets
        if network_rules or virtual_network_subnets:
            pulumi.warn("Public network access is disabled. Network rules will be ignored.")

    if use_managed_identity:
        identity = {"type": "SystemAssigned"}
    else:
        identity = None

    storageaccount: storage.StorageAccount = storage.StorageAccount(
        resource_name=storageacount_name,
        account_name=storageacount_name,
        resource_group_name=resource_group.name,
        location=location,
        sku=storage.SkuArgs(name=sku),
        kind=kind,
        public_network_access=public_network_access,
        default_to_o_auth_authentication=True,
        allow_blob_public_access=allow_blob_public_access,
        allow_shared_key_access=allow_shared_key_access,
        minimum_tls_version=minimum_tls_version,
        is_hns_enabled=is_hns_enabled,
        enable_nfs_v3=nfs_v3,
        enable_https_traffic_only=enable_https_traffic_only,
        access_tier=access_tier_enum,
        identity=identity,
        network_rule_set=network_rule_set_args,
        tags=tags,
    )

    # Create Private Endpoints, can be several (blob, table, queue...)
    if private_endpoints is not None:
        for endpoint in private_endpoints:
            az_private_endpoint(
                resource=storageaccount,
                resource_group=resource_group,
                private_endpoint_config=endpoint,
                tags=tags,
            )

    return storageaccount


def az_storageaccount_from_config(
    config,
    resource_group: resources.ResourceGroup | resources.AwaitableGetResourceGroupResult,
) -> storage.StorageAccount:
    if not resource_group and not config.resource_group:
        raise ValueError("Either resource_group or resource_group_name must be set")

    return az_storageaccount(
        workload_name=config.workload_name,
        env=config.env,
        location=config.location,
        resource_group=resource_group,
        kind=config.kind,
        sku=config.sku,
        minimum_tls_version=config.minimum_tls_version,
        allow_blob_public_access=config.allow_blob_public_access,
        allow_shared_key_access=config.allow_shared_key_access,
        enable_https_traffic_only=config.enable_https_traffic_only,
        nfs_v3=config.nfs_v3,
        use_managed_identity=config.use_managed_identity,
        virtual_network_subnets=config.virtual_network_subnets,
        private_endpoints=config.private_endpoints,
        public_network_access=config.public_network_access,
        is_hns_enabled=config.is_hns_enabled,
        access_tier=config.access_tier,
        network_rules=config.network_rules,
        tags=config.tags,
    )


@dataclass(kw_only=True, frozen=True)
class StorageAccountConfig(StackConfig):
    kind: Optional[str] = "StorageV2"
    sku: Optional[str] = "Standard_LRS"
    minimum_tls_version: Optional[str] = "TLS1_2"
    allow_blob_public_access: Optional[bool] = False
    allow_shared_key_access: Optional[bool] = False
    enable_https_traffic_only: Optional[bool] = True
    nfs_v3: Optional[bool] = False
    use_managed_identity: Optional[bool] = True
    virtual_network_subnets: Optional[List[str]] = None
    public_network_access: Optional[str] = "Disabled"
    is_hns_enabled: Optional[bool] = False
    access_tier: Optional[str] = "Hot"
    network_rules: Optional[List[str]] = None
    private_endpoints: Optional[list[PrivateEndpointConfig]] = None


def storageaccount_deploy() -> None:
    config: StorageAccountConfig = Confy(StorageAccountConfig).populate()

    # Resource Group
    az_rg: resources.ResourceGroup | resources.AwaitableGetResourceGroupResult = az_resource_group_from_config(
        config=config
    )

    pulumi.export("resource_group_name", az_rg.name)

    # Storage Account
    az_storageaccount = az_storageaccount_from_config(config=config, resource_group=az_rg)
    pulumi.export("storageaccount_name", az_storageaccount.name)

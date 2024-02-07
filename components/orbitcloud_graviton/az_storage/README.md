# Azure Storage Account Module
This module provisions an Azure Storage Account with configurable parameters for advanced networking features like IP filtering, access tiers, and private endpoint creation.

## Quickstart

To use this module in its simplest form, you only need to provide a name for the storage account.

```yaml
config:
  azure-native:location: northeurope
  storageaccount:workload_name: myStorageAccount
  storageaccount:env: dev
```

## Configuration Options

#### Networking

##### IP Filtering
To be used to allow traffic from *public IP addresses*
> [!NOTE]
> network_rules will only be effective if public_network_access is set to Enabled.
> Private IPs will be ignored.

```yaml
config:
  storageaccount:public_network_access: Enabled
  storageaccount:network_rules:
    - "93.94.10.0/24"
    - "157.97.5.193"
```

##### Virtual Networks
> [!NOTE]
> virtual_network_subnets will only be effective if public_network_access is set to Enabled

```yaml
config:
  storageaccount:public_network_access: Enabled
  storageaccount:virtual_network_subnets:
    - "/subscriptions/{sub-id}/resourceGroups/{rg-name}/providers/Microsoft.Network/virtualNetworks/{vnet-name}/subnets/{subnet-name}"
    - "/subscriptions/{sub-id}/resourceGroups/{rg-name}/providers/Microsoft.Network/virtualNetworks/{vnet-name}/subnets/{another-subnet-name}"
```

##### Private Endpoints

To configure Private Endpoints, define both the target_resource_type and the corresponding subnet_id. Additionally, if a private_dns_zone_id is provided, the module will automatically create a DNS record within the specified Private DNS Zone

> [!NOTE]
> For Storage Accounts, 1 Private Endpoint per *type* used is required (blob, queue, file, table..)

```yaml
config:
  storageaccount:private_endpoints:
    - target_resource_type: blob
      subnet_id: /subscriptions/{sub-id}/resourceGroups/{rg-name}/providers/Microsoft.Network/virtualNetworks/{vnet-name}/subnets/{subnet-name}
    - target_resource_type: table
      subnet_id: /subscriptions/{sub-id}/resourceGroups/{rg-name}/providers/Microsoft.Network/virtualNetworks/{vnet-name}/subnets/{subnet-name}
      private_dns_zone_id: /subscriptions/{sub-id}/resourceGroups/{rg-name}/providers/Microsoft.Network/privateDnsZones/{private-dns-zone-name}
```

## All settings

Below is a sample YAML configuration for the Pulumi Azure Storage Account module with all parameters specified, including their default values where appropriate:

```yaml
config:
  azure-native:location: northeurope
  storageaccount:workload_name: myStorageAccount # Required
  storageaccount:env: dev # Required
  storageaccount:public_network_access: Enabled # Default is 'Disabled'
  storageaccount:kind: StorageV2 # Default is 'StorageV2'
  storageaccount:sku: Standard_LRS # Default is 'Standard_LRS'
  storageaccount:minimum_tls_version: TLS1_2 # Default is 'TLS1_2'
  storageaccount:allow_blob_public_access: false # Default is `false`
  storageaccount:allow_shared_key_access: false # Default is `false`
  storageaccount:enable_https_traffic_only: true # Default is `true`
  storageaccount:nfs_v3: false # Default is `false`
  storageaccount:use_managed_identity: true # Default is `true`
  storageaccount:is_hns_enabled: false # Default is `false`
  storageaccount:access_tier: Hot # Default is 'Hot'
  storageaccount:network_rules:
    - "93.94.10.0/24"
    - "157.97.5.193"
  storageaccount:virtual_network_subnets:
    - "/subscriptions/{sub-id}/resourceGroups/{rg-name}/providers/Microsoft.Network/virtualNetworks/{vnet-name}/subnets/{subnet-name}"
    - "/subscriptions/{sub-id}/resourceGroups/{rg-name}/providers/Microsoft.Network/virtualNetworks/{vnet-name}/subnets/{another-subnet-name}"
  storageaccount:private_endpoints:
    - target_resource_type: blob
      subnet_id: "/subscriptions/{sub-id}/resourceGroups/{rg-name}/providers/Microsoft.Network/virtualNetworks/{vnet-name}/subnets/{subnet-name}"
    - target_resource_type: table
      subnet_id: "/subscriptions/{sub-id}/resourceGroups/{rg-name}/providers/Microsoft.Network/virtualNetworks/{vnet-name}/subnets/{subnet-name}"
      private_dns_zone_id: "/subscriptions/{sub-id}/resourceGroups/{rg-name}/providers/Microsoft.Network/privateDnsZones/{private-dns-zone-name}"
  storageaccount:tags:
    project: Pulumi Sample
    owner: DevOps Team
```

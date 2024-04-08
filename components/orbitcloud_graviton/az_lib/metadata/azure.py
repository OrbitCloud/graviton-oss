from typing import Any

"""
Container Apps
"""
_app: dict[str, Any] = {
    "ContainerApp": {
        "naming": {
            "prefix": "app",
        },
    },
    "Certificate": {
        "naming": {
            "prefix": "caecert-",
        },
    },
    "ManagedEnvironment": {
        "naming": {
            "prefix": "cae",
            "max_length": 60,
        }
    },
}

"""
App Configuration
"""
_appconfiguration: dict[str, Any] = {
    "ConfigurationStore": {
        "namespace": "Microsoft.AppConfiguration/configurationStores",
        "sub_resource_name": "configurationStore",
        "naming": {
            "prefix": "appcs",
        },
        "public_dns_zone": "azconfig.io",
        "private_dns_zone": "privatelink.azconfig.io",
    },
    "KeyValue": {
        "naming": {
            "prefix": "appcsk",
        },
    },
}

"""
Azure IAM
"""
_authorization: dict[str, Any] = {
    "RoleAssignment": {
        "naming": {
            "prefix": "iam",
        },
    },
}

"""
Container Registry
"""
_containerregistry: dict[str, Any] = {
    "Registry": {
        "naming": {
            "prefix": "cr",
            "alphanumeric": True,
        },
        "sub_resource_name": "registry",
        "namespace": "Microsoft.ContainerRegistry/registries",
        "public_dns_zone": "azurecr.io",
        "private_dns_zone": "privatelink.azurecr.io",
    },
}

"""
Event Grid
"""
_eventgrid: dict[str, Any] = {
    "Domain": {
        "naming": {
            "prefix": "evgd",
        },
        "namespace": "Microsoft.EventGrid/domains",
        "sub_resource_name": "domain",
        "private_dns_zone": "privatelink.eventgrid.azure.net",
    },
    "DomainTopic": {
        "naming": {
            "prefix": "evgt",
        },
        "namespace": "Microsoft.EventGrid/topics",
        "sub_resource_name": "topic",
        "private_dns_zone": "privatelink.eventgrid.azure.net",
    },
}

"""
Event Hub
"""
_eventhub: dict[str, Any] = {
    "Namespace": {
        "naming": {
            "prefix": "evhns",
        },
        "namespace": "Microsoft.EventHub/namespaces",
        "sub_resource_name": "namespace",
        "private_dns_zone": "privatelink.servicebus.windows.net",
    },
    "Eventhub": {
        "naming": {
            "prefix": "evh",
        },
    },
    "NamespaceAuthorizationRule": {
        "naming": {
            "prefix": "evhns-key",
        },
    },
}
"""
App Insights
"""
_insights: dict[str, Any] = {
    "Component": {
        "naming": {
            "prefix": "appi",
        },
    },
    "Diagnosticsetting": {
        "naming": {
            "prefix": "diag",
        },
    },
}

"""
Key Vault
"""
_keyvault: dict[str, Any] = {
    "Vault": {
        "naming": {
            "prefix": "kv",
            "alphanumeric": True,
            "max_length": 24,
        },
        "namespace": "Microsoft.KeyVault/vaults",
        "sub_resource_name": "vault",
        "public_dns_zone": "vault.azure.net",
        "private_dns_zone": "privatelink.vaultcore.azure.net",
    },
    "Secret": {
        "naming": {
            "prefix": "kvs",
        },
    },
}

"""
Network
"""
_network: dict[str, Any] = {
    "VirtualNetwork": {
        "namespace": "Microsoft.Network/virtualNetworks",
        "naming": {
            "prefix": "vnet",
        },
    },
    "PrivateDnsZoneGroup": {
        "namespace": "Microsoft.Network/privateDnsZoneGroups",
        "naming": {
            "prefix": "pdzg",
        },
    },
    "Subnet": {
        "namespace": "Microsoft.Network/virtualNetworks/subnets",
        "sub_resource_name": "subnet",
        "naming": {
            "prefix": "snet",
        },
    },
    "VirtualWan": {
        "naming": {
            "prefix": "vwan",
        },
    },
    "VirtualHub": {
        "naming": {
            "prefix": "vhub",
        },
    },
    "VpnServerConfiguration": {
        "naming": {
            "prefix": "vpnconf",
        },
    },
    "P2sVpnGateway": {
        "naming": {
            "prefix": "vpng",
        },
    },
    "HubVirtualNetworkConnection": {
        "naming": {
            "prefix": "vhubc",
        },
    },
    "Zone": {
        "naming": {
            "prefix": "dns",
        },
    },
    "RecordSet": {
        "naming": {
            "prefix": "dnsr,",
        },
    },
    "PrivateRecordSet": {
        "naming": {
            "prefix": "dnsr",
        },
    },
    "PrivateEndpoint": {
        "naming": {
            "prefix": "pep",
        },
    },
}

"""
Azure Monitor / Log Analytics
"""
_operationalinsights: dict[str, Any] = {
    "Workspace": {
        "naming": {
            "prefix": "log",
        },
    },
}

"""
Azure Provider Registration
"""
_providerhub: dict[str, Any] = {
    "ProviderRegistration": {
        "naming": {
            "prefix": "proreg",
        },
    },
    "ResourceTypeRegistration": {
        "naming": {
            "prefix": "prov",
        },
    },
}

"""
Resources
"""
_resources: dict[str, Any] = {
    "ResourceGroup": {
        "namespace": "Microsoft.Resources/resourceGroups",
        "resource_type": "resourceGroup",
        "naming": {
            "prefix": "rg",
        },
    },
}

"""
Storage
"""
_storage: dict[str, Any] = {
    "StorageAccount": {
        "namespace": "Microsoft.Storage/storageAccounts",
        "resource_type": "Microsoft.Storage/storageAccounts/storageAccount",
        "naming": {
            "prefix": "st",
            "alphanumeric": True,
            "lowercase": True,
        },
    },
    "Table": {
        "namespace": "Microsoft.Storage/storageAccounts/tableServices",
        "resource_type": "storageAccounts/tableServices/tables",
        "sub_resource_name": "table",
        "naming": {
            "prefix": "sttbl",
        },
        "private_dns_zone": "privatelink.table.core.windows.net",
    },
    "Queue": {
        "namespace": "Microsoft.Storage/storageAccounts/queueServices",
        "resource_type": "storageAccounts/queueServices/queues",
        "sub_resource_name": "queue",
        "naming": {
            "prefix": "stq",
        },
        "private_dns_zone": "privatelink.queue.core.windows.net",
    },
    "BlobContainer": {
        "namespace": "Microsoft.Storage/storageAccounts/blobServices",
        "resource_type": "storageAccounts/blobServices/containers",
        "sub_resource_name": "blob",
        "naming": {
            "prefix": "stbc",
        },
        "private_dns_zone": "privatelink.blob.core.windows.net",
    },
    "FileShare": {
        "namespace": "Microsoft.Storage/storageAccounts/fileServices",
        "resource_type": "storageAccounts/fileServices/shares",
        "sub_resource_name": "file",
        "naming": {
            "prefix": "stfs",
        },
        "private_dns_zone": "privatelink.file.core.windows.net",
    },
}

"""
Azure App Service
"""
_web: dict[str, Any] = {
    "AppServicePlan": {"prefix": "asp"},
    "WebApp": {
        "naming": {
            "prefix": "app",
        },
        "namespace": "Microsoft.Web/sites",
        "sub_resource_name": "site",
        "public_dns_zone": "azurewebsites.net",
        "private_dns_zone": "privatelink.azurewebsites.net",
    },
}

_azure_resource_meta: dict[str, Any] = {
    "pulumi_azure_native": {
        "app": {
            "namespace": "Microsoft.App",
            "resources": _app,
        },
        "appconfiguration": {
            "namespace": "Microsoft.AppConfiguration",
            "resources": _appconfiguration,
        },
        "authorization": {
            "namespace": "Microsoft.Authorization",
            "resources": _authorization,
        },
        "containerregistry": {
            "namespace": "Micrsoft.ContainerRegistry",
            "resources": _containerregistry,
        },
        "eventgrid": {
            "namespace": "Microsoft.EventGrid",
            "resources": _eventgrid,
        },
        "eventhub": {
            "namespace": "Microsoft.EventHub",
            "resources": _eventhub,
        },
        "insights": {
            "namespace": "Microsoft.Insights",
            "resources": _insights,
        },
        "keyvault": {
            "namespace": "Microsoft.KeyVault",
            "resources": _keyvault,
        },
        "network": {
            "namespace": "Microsoft.Network",
            "resources": _network,
        },
        "operationalinsights": {
            "namespace": "Microsoft.OperationalInsights",
            "resources": _operationalinsights,
        },
        "providerhub": {
            "resources": _providerhub,
        },
        "resources": {
            "namespace": "Microsoft.Resources",
            "resources": _resources,
        },
        "sql": {},
        "storage": {
            "namespace": "Microsoft.Storage",
            "resources": _storage,
        },
        "web": {
            "namespace": "Microsoft.Web",
            "resources": _web,
        },
    }
}

_azure_regions: dict[str, dict[str, str]] = {
    "northeurope": {
        "name": "North Europe",
        "abbr": "neu",
    },
    "westeurope": {
        "name": "West Europe",
        "abbr": "weu",
    },
    "swedencentral": {
        "name": "Sweden Central",
        "abbr": "sec",
    },
    "norwayeast": {
        "name": "Norway East",
        "abbr": "noe",
    },
    "norwaywest": {
        "name": "Norway West",
        "abbr": "now",
    },
}

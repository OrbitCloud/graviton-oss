from typing import Literal

SubnetServiceEndpoints = Literal[
    "Microsoft.AzureActiveDirectory",
    "Microsoft.AzureCosmosDB",
    "Microsoft.CognitiveServices",
    "Microsoft.ContainerRegistry",
    "Microsoft.EventHub",
    "Microsoft.KeyVault",
    "Microsoft.ServiceBus",
    "Microsoft.Sql",
    "Microsoft.Storage",
    "Microsoft.Storage.Global",
    "Microsoft.Web",
]

SPECIAL_SUBNETS = {
    "GatewaySubnet",
    "AzureFirewallManagementSubnet",
    "AzureFirewallSubnet",
    "AzureBastionSubnet",
}

NON_NSG_SUBNETS = {"GatewaySubnet", "AzureFirewallSubnet", "AzureFirewallManagementSubnet"}

# Automatic naming

The required `env`, `location` and `workload_name` [stack configurations](./stacks/)
are used to automatically generate names for the cloud resources created. Names
for resources can often be set explicitly though, especiallyy for services with
global uniqueness requirements like Storage Accounts, Key Vaults, Container
Registries etc.

## Naming conventions

In general, we follow the following naming conventions:

`{resource_type}-{workload_name}-{env}-{location}-{instance}`

For example a resource group might be named `rg-myapp-dev-westus-01`

!!! info "Azure best practices"
    - [Abbreviation recommendations for Azure resources](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/azure-best-practices/resource-abbreviations)
    - [Naming conventions for Azure resources](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/azure-best-practices/resource-naming)

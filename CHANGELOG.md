## v0.32.0 (2024-03-01)

### Feat

- **ContainerAppEnv**: Automate creation of DNS records needed for custom domain configuration
- **LandingZone**: Add DnsZone with AcmeSsl deployment options
- **DnsZone**: Ability to create NS records for child in an existing parent zone
- **az_lib**: Add StrRef, SecretStrRef and DictRef stack reference types
- **AcmeSsl**: New component for acquiring wildcard plus certificates via DNS challenge
- **AzureBase**: Add helper for stack exports and skip_exports & exports_prefix options
- **AzureBase**: Add exports for subscriptionId, tenantId, location, env and workload name
- **DnsZone**: Allow "*" as record relative name for wildcard records
- **DnsZone**: Make .record publicly accessible

### Fix

- **diagnostic_settings**: Revert attempt to fix constant parameter change detection during refreshes
- **EventHub**: Fix hub naming and adjust parents/dependencies
- **debugpy**: Fix VScode launch options
- **EntraApp**: Add stack exports
- **KeyVault**: Add AzurePolicyEvaluationDetails to diagnostic logging
- **pulumi_lib**: Fix a bug where dash_formatted helper would take strings as list sequences
- **DnsZone**: Fix TXT record input types
- **AzMonitor**: Add parameter causing constant change detection
- **config**: Generate JSON schema before validation

## v0.31.0 (2024-02-28)

### Feat

- Oracle queue notifications to Azure Event hub  (#162)

## v0.30.0 (2024-02-17)

### Feat

- **app_insights**: Add instrumentation key and connection string as secret outputs
- **DnsZone**: Add component for public dns zones

### Fix

- **StorageAccount**: Add optional stack output prefix in cases a stack has many storage accounts

## v0.29.0 (2024-02-17)

### Feat

- **AcmeEntraApp**: Implement base for creating an Entra App for managing acme_challenge TXT records

## v0.28.0 (2024-02-17)

### Feat

- **LandingZone**: IAM assignments to deployment principal for managing remote vnet

## v0.27.0 (2024-02-15)

### Feat

- **AppZone**: Adds Storage Account with network restrictions and storage tables
- **stack-schema**: Add automatic json schema generation for YAML validation in bases

## v0.26.0 (2024-02-15)

### Feat

- **AppZone**: Integrate Application Insights with DAPR in ContainerAppEnv
- **az_monitor**: Add Application Insights component
- **KeyVault**: Audit logs and metrics configured for Key Vault

## v0.25.0 (2024-02-14)

### Feat

- **AppZone**: Adds AppZone base for deploying application landing zones
- **stack_schema**: Module for generating JSON validation schema from Pydantic models
- **KeyVault**: Allow explicitly setting KeyVault name when needed due to global unique constrains
- **config**: Adds support for getting nested values from dictionary stack outputs
- **LandingZone**: Configures diagnistoc settings for EventHub
- **EventHub**: Adds diagnostic_settings to EventHub for logs & metrics
- **az_network**: Implements vhub connections in vhub
- **az_lib**: Adds AzureNameRef data type for resolving resource name references
- **keyvault**: Adds network configuration options and implements Secret module
- **landing_zone**: Adds log workspace to landing zone

### Fix

- **AzureIdRef**: Fixes an issue when same stack output is referenced twice in same stack
- **KeyVault**: Allowed vnets should be subnet IDs
- **VNet**: Fixes stack export of subnets
- **type**: Various type improvements

### Refactor

- **ContainerAppEnv+az_monitor**: Refactors ContainerAppEnv and diagnostic_settings
- **az_lib**: Moves resource name prefixes to a seperate file
- **entra_app**: Use Literal for audience options instead of Enum
- **containerapp-env**: Changes to module imports

## 0.24.0 (2024-02-12)

## v0.24.0 (2024-02-12)

## v0.23.0 (2024-02-12)

## v0.22.0 (2024-02-12)

## v0.21.0 (2024-02-09)

## v0.20.0 (2024-02-09)

### Feat

- **StorageAccount**: Adds option to create storage tables

## v0.19.0 (2024-02-09)

* feat(vnet): Adds support for subnet service endpoints
* ci: Uses Graviton bot to release


## v0.18.0 (2024-02-07)

### Feat

- **config**: Adds IdReference type for retrieving and validating resource IDs
- **containerapp_env**: Remove az_managed_environment.py
- **eventhub**: Adds EventHub component
- **containerapp_env**: Networking, custom_domain, certificates, logging
- **landing_zone**: Adds hub environment
- **hubspoke**: Simplifies hubspoke base usage
- **oidc-app**: Adds base config for azuread provider and changes naming convention for keyvault
- **az_network**: Adds P2S VPN gateway
- **az_network**: Adds P2S VPN Gateway
- **az_network**: Adds Virtual Wan and Virtual Hub
- **config**: Introduce the use of Pydantic config schemas
- **pydantic**: Pydantic models for managing Pulumi configs
- **landing_zone**: Adopt Pulumi ESC env to configure stack

### Fix

- **pulumi-opts**: Fixes merge order of Pulumi opts in component resources
- **keyvault**: Go back to alphanumeric naming with random suffix due to globally unique naming constrains
- **pulumi-esc**: Fix typo in ESC config output and add tenantId to azuread provider
- **esc-config**: Fixes azure-native config
- **PulumiConfig**: Returns default value when value isn't provided
- **PulumiConfig**: Adds support for Optional nested BaseModels
- **PulumiConfig**: Fixes an error in model validation
- **config**: Fixes a bug in boolean stack config parameters
- **pyproject.toml**: Remove landing_site base from package
- **entra_app**: Small fixes and improvements to OIDC app
- **merge**: Fixes merge conflict and az_storageaccount typing

### Refactor

- **containerapp-env**: Improves certificate and custom domain configuration and validation
- **containerapp-env**: Improves certificate configuration
- **containerapp-env**: Simplifies VNET configuration
- **containerapp-env**: Improves workload profile configuration
- **StorageAccount**: Refactors StorageAccount module
- **EntraApp**: Refactors Entra App module and IaM assignments
- **eventhub**: Adds EventHub exports
- **dev**: Removes networking dev scratchpad
- **oidc-app**: Changes app name to pulumi-<env>-deployments
- **keyvault**: Migrates keyvault to new config structure
- **acr+keyvault**: Adopts new config schema
- **az_network**: Moves VnetConfig and SubnetConfig to _vnet.py
- **cleanup**: Removes unused files
- **landing_zone**: Reorganizing main.py
- **landing_zone**: Adds pulumiConfig parameters to ESC env output
- **multiple**: Adds landing zone base and various improvements

## v0.17.0 (2024-02-02)

### Feat

- initial storageaccount, privateendpoint, privatednszonegroup #30 #19 #25

### Refactor

- **resource_namer**: Minor improvement and added test for storage account naming

## v0.16.0 (2024-01-10)

### Feat

- **ruff**: Replaces pylint, black & flake8 with Ruff

## v0.15.0 (2023-09-19)

### Feat

- **build.yml**: Triggering version bump

## v0.14.0 (2023-09-19)

### Feat

- **build.yml**: Triggering version bump

## v0.14.0rc1 (2023-09-19)

### Feat

- **build.yml**: Triggering version bump

## v0.14.0rc0 (2023-09-19)

### Feat

- **build.yml**: Triggering version bump

## v0.13.0 (2023-09-19)

### Feat

- **build.yml**: Triggering version bump

## v0.12.0 (2023-09-19)

### Feat

- **build.yml**: Triggering version bump

## v0.11.0 (2023-09-19)

### Feat

- **actionlint**: Adding actionlint config

## v0.10.0 (2023-09-18)

### Feat

- **build.yml**: Fixing tag-check version bump
- **build.yml**: Fixing tag-check version bump

## v0.9.0 (2023-09-18)

### Feat

- **build.yml**: Fixing tag-check version bump

## v0.8.0 (2023-09-18)

### Feat

- **build.yml**: Intentional version bump test

## v0.7.0 (2023-09-18)

### BREAKING CHANGE

- Intentional
- Intentionally marked as breaking change

### Feat

- **Manually-updating-cz-version**: Bumping version to trigger build workflow release
- **Bump-version-manually-to-0.6**: Attempt to figure out release error
- **Update-readme,-triggering-version-bump**: N/a

## v0.5.0 (2023-09-18)

### Feat

- **Lots-of-additions,-including-breaking-changes**: New components and bases added. Project structure refactored. Improved dev tooling

## v0.4.0 (2023-09-04)

### Feat

- **Devcontainer-and-monorepo-workspace-settings-added**: Had to split up devcontainer.json into different settings.json, configured Pyright and various other things

## v0.3.0 (2023-09-04)

### BREAKING CHANGE

- Changed the parameter order in az_resource_group

### Refactor

- **Improved-tests-and-testability-within-components**: Added the capability to run pytest tests in parallel workers

## v0.2.0 (2023-08-30)

### Feat

- Adding commitizen and dunamai

## v0.1.0 (2023-08-30)

## v0.47.1 (2024-04-16)

### Fix

- **typing**: Fix typing after Pulumi 3.113 update (#238)

## v0.47.0 (2024-04-16)

### Feat

- ESC Azure Environments (#237)

## v0.46.2 (2024-04-15)

### Refactor

- **az_lib**: Change AzureBase name to AzureStack (#231)

## v0.46.1 (2024-04-10)

### Fix

- Add missing metadata and private endpoints (#225)

## v0.46.0 (2024-04-10)

### Feat

- **pulumi_lib**: Add TimeFromNow datatype (#224)

## v0.45.0 (2024-04-10)

### Feat

- **az_ai**: Add Azure AI search component (#223)

## v0.44.0 (2024-04-10)

### Feat

- **ContainerApp**: Add option for ingress IP restrictions (#222)

## v0.43.0 (2024-04-08)

### Feat

- Azure Metadata & private link DNS zone rework (#218)

## v0.42.0 (2024-03-26)

### Feat

- Add component for Private DNS Resolver, added to hubspoke base (#206)

## v0.41.0 (2024-03-20)

### Feat

- **EventGridDomain**: Add Event Grid Domain component (#203)

## v0.40.0 (2024-03-19)

### Feat

- Private DNS Zones (#202)

## v0.39.0 (2024-03-19)

### Feat

- App Workload Dependencies (#201)

## v0.38.0 (2024-03-19)

### Feat

- Application Configuration (#200)

## v0.37.0 (2024-03-18)

### Feat

- **LandingZone**: Add Workload identities (#199)

## v0.36.1 (2024-03-12)

### Refactor

- Use pulumi-acme provider instead of lego cli (#190)

## 0.36.0 (2024-03-11)

### BREAKING CHANGE

- Intentional
- Intentionally marked as breaking change
- Testing breaking change
- Changed the parameter order in az_resource_group

### Feat

- **AppWorkload**: Base for deploying Azure Container Apps
- **acmessl**: Stop using staging server by default for cert creation
- **workload_identities**: Add base for managing Entra Apps with OIDC credentials
- **copier**: Add copier and component class template (#168)
- Oracle queue notifications to Azure Event hub  (#162)
- **ContainerAppEnv**: Automate creation of DNS records needed for custom domain configuration
- **LandingZone**: Add DnsZone with AcmeSsl deployment options
- **DnsZone**: Ability to create NS records for child in an existing parent zone
- **az_lib**: Add StrRef, SecretStrRef and DictRef stack reference types
- **AcmeSsl**: New component for acquiring wildcard plus certificates via DNS challenge
- **AzureBase**: Add helper for stack exports and skip_exports & exports_prefix options
- **AzureBase**: Add exports for subscriptionId, tenantId, location, env and workload name
- **DnsZone**: Allow "*" as record relative name for wildcard records
- **DnsZone**: Make .record publicly accessible
- **app_insights**: Add instrumentation key and connection string as secret outputs
- **DnsZone**: Add component for public dns zones
- **AcmeEntraApp**: Implement base for creating an Entra App for managing acme_challenge TXT records
- **LandingZone**: IAM assignments to deployment principal for managing remote vnet
- **stack-schema**: Add automatic json schema generation for YAML validation in bases
- **AppZone**: Integrate Application Insights with DAPR in ContainerAppEnv
- **az_monitor**: Add Application Insights component
- **KeyVault**: Audit logs and metrics configured for Key Vault
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
- **StorageAccount**: Adds option to create storage tables
- **vnet**: Adds support for subnet service endpoints
- **config**: Adds IdReference type for retrieving and validating resource IDs
- **containerapp_env**: Remove az_managed_environment.py
- **eventhub**: Adds EventHub component
- **containerapp_env**: Networking, custom_domain, certificates, logging
- **hubspoke**: Simplifies hubspoke base usage
- **oidc-app**: Adds base config for azuread provider and changes naming convention for keyvault
- **az_network**: Adds P2S VPN gateway
- **az_network**: Adds P2S VPN Gateway
- **az_network**: Adds Virtual Wan and Virtual Hub
- **config**: Introduce the use of Pydantic config schemas
- **pydantic**: Pydantic models for managing Pulumi configs
- initial storageaccount, privateendpoint, privatednszonegroup #30 #19 #25
- **ruff**: Replaces pylint, black & flake8 with Ruff
- **build.yml**: Triggering version bump
- **build.yml**: Triggering version bump
- **build.yml**: Triggering version bump
- **build.yml**: Triggering version bump
- **build.yml**: Triggering version bump
- **build.yml**: Triggering version bump
- **actionlint**: Adding actionlint config
- **build.yml**: Fixing tag-check version bump
- **build.yml**: Fixing tag-check version bump
- **build.yml**: Fixing tag-check version bump
- **build.yml**: Intentional version bump test
- **Manually-updating-cz-version**: Bumping version to trigger build workflow release
- **Bump-version-manually-to-0.6**: Attempt to figure out release error
- **Update-readme,-triggering-version-bump**: N/a
- **Lots-of-additions,-including-breaking-changes**: New components and bases added. Project structure refactored. Improved dev tooling
- **Devcontainer-and-monorepo-workspace-settings-added**: Had to split up devcontainer.json into different settings.json, configured Pyright and various other things
- Adding commitizen and dunamai

### Fix

- **pyproject**: Include app_workload in package
- **json_schema**: Add final newline to .json file for pre-commit validation
- **workload_identities**: Include base in pyproject.toml
- **diagnostic_settings**: Revert attempt to fix constant parameter change detection during refreshes
- **EventHub**: Fix hub naming and adjust parents/dependencies
- **debugpy**: Fix VScode launch options
- **EntraApp**: Add stack exports
- **KeyVault**: Add AzurePolicyEvaluationDetails to diagnostic logging
- **pulumi_lib**: Fix a bug where dash_formatted helper would take strings as list sequences
- **DnsZone**: Fix TXT record input types
- **AzMonitor**: Add parameter causing constant change detection
- **config**: Generate JSON schema before validation
- **StorageAccount**: Add optional stack output prefix in cases a stack has many storage accounts
- **AzureIdRef**: Fixes an issue when same stack output is referenced twice in same stack
- **KeyVault**: Allowed vnets should be subnet IDs
- **VNet**: Fixes stack export of subnets
- **type**: Various type improvements
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

- **EntraApp**: Adjust naming to include workload+env
- **ContainerAppEnv+az_monitor**: Refactors ContainerAppEnv and diagnostic_settings
- **az_lib**: Moves resource name prefixes to a seperate file
- **entra_app**: Use Literal for audience options instead of Enum
- **containerapp-env**: Changes to module imports
- **containerapp-env**: Improves certificate and custom domain configuration and validation
- **containerapp-env**: Improves certificate configuration
- **containerapp-env**: Simplifies VNET configuration
- **containerapp-env**: Improves workload profile configuration
- **StorageAccount**: Refactors StorageAccount module
- **EntraApp**: Refactors Entra App module and IaM assignments
- **eventhub**: Adds EventHub exports
- **oidc-app**: Changes app name to pulumi-<env>-deployments
- **keyvault**: Migrates keyvault to new config structure
- **acr+keyvault**: Adopts new config schema
- **az_network**: Moves VnetConfig and SubnetConfig to _vnet.py
- **cleanup**: Removes unused files
- **landing_zone**: Reorganizing main.py
- **landing_zone**: Adds pulumiConfig parameters to ESC env output
- **resource_namer**: Minor improvement and added test for storage account naming
- **multiple**: Adds landing zone base and various improvements
- **Improved-tests-and-testability-within-components**: Added the capability to run pytest tests in parallel workers

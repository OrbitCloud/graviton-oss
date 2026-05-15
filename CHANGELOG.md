## v0.94.0 (2026-05-15)

### Feat

- **datazone**: add datazone base orchestrating psql, mysql, sql, storage
- **az_mysql**: add MySQL Flexible Server component

## v0.93.1 (2026-03-29)

### Fix

- **ci**: pass bot token via input to action-gh-release

## v0.93.0 (2026-03-29)

### Feat

- **SqlServer**: Support VirtualNetworkRules

### Fix

- **tests**: update metadata snapshot for VirtualNetworkRule
- **PostgresFlexibleServer**: Remove unneeded encryption parameter

## v0.92.0 (2026-03-03)

### Feat

- **development**: add example stacks for all 14 Graviton CDK base types (#250)

## v0.91.0 (2026-02-27)

### Feat

- **az_lib**: replace Python dict metadata with YAML service files (#244)

## v0.90.0 (2026-02-26)

### Feat

- **az_app**: Add managed storage and volume mount support

## v0.89.0 (2026-02-18)

### Feat

- **PostgresFlexibleServer**: Bump default major version to 18
- **VirtualNetwork**: Add support for route tables

### Refactor

- **AppServicePlan**: Implement enum.StrEnum

## v0.88.2 (2025-11-20)

### Fix

- **AzureStack**: Validation failures after Pydantic update fixed

## v0.88.1 (2025-11-13)

### Fix

- **ContainerApp**: Allow explicit naming on managed cert name

## v0.88.0 (2025-09-18)

### Feat

- **OracleDatabase**: Add repo and install azure-vm-tools
- **DnsZone**: Loosen validation on relative names for MX, DKIM & DMARC records
- **DnsZone**: Add ability to enable DNSSEC
- **VirtualMachine**: Allow data disks to reside in different zone from VM

### Fix

- **DnsZone**: Provide multiple TXT record values correctly

## v0.87.1 (2025-08-13)

### Fix

- **ContainerApp**: Reduce managed cert name length to fit within Azure naming restrictions

## v0.87.0 (2025-06-19)

### BREAKING CHANGE

- This might cause replacement on databases – please set name explicitly to current name to escape that

### Feat

- **ContainerApp**: Allow setting registry reference manually
- **SqlDatabase**: Do not prefix/suffix database names

### Fix

- **StorageAccount**: Endpoints for tables, queues & files not being exposed

### Refactor

- **EntraApp**: Migrate from deprecated end_date_relative to end_date for application passwords

## v0.86.0 (2025-05-16)

### Feat

- **PostgresFlexibleServer**: Allow configuring server IOPS
- **SqlServer**: Support configuring non-entra administrators
- **ContainerApp**: Support for creating custom domain DNS records automatically

### Fix

- **ContainerApp**: App Permissions and outputs accidentally missing for non-custom domain apps

## v0.85.1 (2025-04-08)

### Fix

- **hubspoke**: Outputs fixed when multiple dns zones are configured

## v0.85.0 (2025-03-25)

### Feat

- **AzureOpenAi**: Add Private Endpoint configuration option
- **hubspoke**: Support provisioning multiple DNS zones

## v0.84.2 (2025-03-20)

### Fix

- **az_lib**: Add missing naming prefix for container app env certificate resource

## v0.84.1 (2025-03-20)

### Fix

- **ContainerApp**: KeyVault secret references using system assigned identities fixed
- **ContainerApp**: Remove trailing slash from CORS origins

## v0.84.0 (2025-03-14)

### Feat

- **ContainerApp**: Support auto issued managed SSL certificates

## v0.83.0 (2025-03-13)

### Feat

- **app_zone**: Add possibility to optionally deploy Service Bus
- **ServiceBus**: Add component for provisioning Azure Service Bus

## v0.82.0 (2025-03-12)

### Feat

- **AzureOpenAi**: Add Azure OpenAi component

### Refactor

- **ResourceOptions**: Use .merge instead of deprecated (and private) ._merge_instances

## v0.81.0 (2025-02-26)

### Feat

- **SearchService**: Add diagnostic settings to AI Search component

## v0.80.0 (2025-02-26)

### Feat

- **ContainerApp**: Add support for Azure tags
- **ContainerApp**: Ability to ignore image tag updates, f.x. done by CICD

### Refactor

- **ContainerApp**: Only provide additional port mappings when present

## v0.79.0 (2025-02-25)

### Feat

- **EventHub**: Allow CIDR format for firewall IP rules
- **KeyVault**: Add support for private endpoints

## v0.78.0 (2025-02-12)

### Feat

- **ContainerApp**: Support key vault referenced and volume mounted secrets
- **ContainerApp**: Allow additional TCP ingress ports

### Fix

- **az_lib**: Support outputs passed to StrRef

## v0.77.0 (2025-02-10)

### Feat

- **azuresql**: Add base for deploying Azure SQL workloads
- **az_sql**: Add Azure SQL servers, databases & elastic pools
- **az_iam**: Support creation of user assigned identities
- **az_network**: Add PublicIpv4FirewallRule datatype

## v0.76.0 (2025-01-29)

### Feat

- **EntraApp**: Add possibility to configure custom oauth2 scopes (#42)

## v0.75.0 (2024-12-11)

### Feat

- **AcmeSsl**: Support OIDC token auth for Azure DNS challenge

### Fix

- **StorageAccount**: Default hierarchial namespace parameter to None

## v0.74.0 (2024-11-28)

### Feat

- **az_acr**: Support image retention policy configurations

## v0.73.1 (2024-11-27)

### Fix

- **EntraApp**: Update stack outputs with service principal id and object_id
- **EntraApp**: Use service principal object_id for entra role assignments
- **EventHub**: Only create network rule set when some subnets or ips are configured

## v0.73.0 (2024-11-27)

### Feat

- **storage_account**: Add SFTP and Custom Domain Support

## v0.72.0 (2024-11-21)

### Feat

- **oidc-providers**: Allow defining multiple repos for GitHub OIDC credentials
- **az_lib**: Add colons and slashes to fmt_name() helper

### Fix

- **iam_assignment**: Use service principal object_id instead of id after updating pulumi-azuread
- **ContainerAppEnv**: Fix workload_profiles typing after Pydantic update

## v0.71.1 (2024-11-12)

### Fix

- **az_iam**: Dynamically set subscription ID for auth client

## v0.71.0 (2024-11-12)

### Feat

- **ContainerApp**: Add support for health probes
- **PostgresFlexibleServer**: Add storage & server configuration parameters
- **EventHub**: Add scaling and networking configuration options
- **AzureStack**: Add fq_subscription_id to model (/subscription/... format)
- **ContainerApp**: Add keda scalers & container app jobs

### Fix

- **lib**: Support Pulumi stack secret schema
- **StorageAccount**: Only register outputs for endpoints which are available

### Refactor

- **DnsZone**: Properly merge pulumi ResourceOptions
- **AcmeSsl**: Remove entra_config parameter
- **app_workload**: Improve validation error for colliding app names

## v0.70.0 (2024-10-03)

### Feat

- **ContainerApp**: Add Cors settings

## v0.69.0 (2024-09-30)

### Feat

- **ContainerApp**: Support HTTP resiliency header matches
- **ContainerApp**: Add validation on resiliency configurations

## v0.68.0 (2024-09-30)

### Feat

- **EventHub**: Add auto inflate configuration option
- **EventGridDomain**: Add option to assign azure permissions to managed identity

### Fix

- **ExternalIdTenant**: Remove tenant_id from configuration

## v0.67.0 (2024-09-30)

### BREAKING CHANGE

- ContainerApp: name_prefix wasn't being used for iam_assignment resource_names. Remove name_prefix from your stack config to retain same naming or destroy and reprovision those permissions.

### Feat

- **EventGridDomain**: Use explicit name without Pulumi suffix
- **AzureStack**: Add fq_subscription_id output

### Fix

- **ContainerApp**: use name_prefix when naming iam_assignment resource_names

## v0.66.0 (2024-09-23)

### Feat

- Entra Apps for authentication (#412)

## v0.65.0 (2024-09-23)

### Feat

- Azure Firewall and IP groups (#396)

## v0.64.0 (2024-09-20)

### BREAKING CHANGE

- Could trigger recreation of the resource.

### Feat

- **oracledb**: Add ol9 developer repo, microdnf and rlwrap to cloud-init dependencies
- **PostgresFlexibleServer**: Add current deployment principal as server admin
- **PostgresFlexibleServer**: Add Diagnostic Settings for collecting server logs, query store and metrics
- **PostgresFlexibleServer**: Add admin password to stack exports
- **container_registry**: Allow optional explicit naming of registry
- **AzureStack**: Add azure_environment config from upstream ESC env

### Fix

- **VirtualNetworkGateway**: Pass ResourceOption on to PublicIp
- **PrivateDnsResolver**: Add missing ResourceOption in various places
- **landing_zone**: Only pass in Key Vault to AcmeSsl if present
- **ContainerApp**: Prefix custom_domain exports with https://
- **log_workspace**: Add missing stack export
- **PublicIp**: Remove use of ComponentResource and add missing ResourceOptions
- **az_lib**: Add missing name prefixes
- **ContainerAppEnv**: Fix certificate field typing to allow Pulumi secrets in addition to stack reference
- **entra**: Fix Entra External ID SKU args after pulumi_azure_native update
- Re-add poetry.lock
- **AcmeSsl**: Disable EntraApp authentication in favor of current user auth context

### Refactor

- **oracledb**: Remove unused imports

## v0.63.0 (2024-09-20)

### Feat

- Add Oracle Database VM base (#377)
- **az_backup**: Add Azure Backup component
- **VirtualMachineDisk**: Add bursting, iops and logical sector configuration options
- Entra External Tenants (#386)
- **oracledb**: Enable Oracle Managed Files on new DB creation
- **oracledb**: Add installation scripts
- **OracleDatabase**: Add Oracle Database Azure VM base
- **CloudInitTemplate**: Add cloud-init template component
- **VirtualMachine**: Add support for custom data
- **StorageAccount**: Add support for file shares and SMB security configurations
- **oracledb**: Add base for deploying Oracle Database VM

### Fix

- **jinja**: Enable autoescape to suppress GitHub security warning
- **pyproject**: Include az_compute in package

### Refactor

- **oracledb**: Disable auto download oracle binaries

## v0.62.0 (2024-08-26)

### Feat

- Entra External Tenants (#386)

## v0.61.0 (2024-08-20)

### Feat

- **az_compute**: Add Virtual Machine component
- **az_network**: Add NetworkInterface component

## v0.60.0 (2024-08-19)

### Feat

- **PostgresFlexibleServer**: Support Azure Postgres Flexible Server  (#298)

## v0.59.0 (2024-06-21)

### Feat

- add support for vnet peering (#323)

## v0.58.1 (2024-06-06)

### Fix

- **LandingZone**: Remove pulumi app permissions config parameter no longer used (#314)

## v0.58.0 (2024-06-06)

### Refactor

- **KeyVault**: Enable purge protection by default (#312)

## v0.57.1 (2024-06-03)

### Fix

- **ContainerApp**: Fix https only configurations (#304)

## v0.57.0 (2024-06-01)

### Feat

- ContainerApp resilience and TCP ingress (#299)

## v0.56.0 (2024-05-30)

### Feat

- Add Azure Container Registry "Standard" SKU (#293)

## v0.55.1 (2024-05-28)

### Fix

- **app_workload**: Ensure dependencies are avilable before referencing (#289)

## v0.55.0 (2024-05-28)

### Refactor

- **StorageAccount**: Change default SKU to Premium LRS (#288)

## v0.54.0 (2024-05-28)

### Feat

- **landing_zone**: Add optional search service to base (#287)

## v0.53.0 (2024-05-28)

### Feat

- **ContainerApp**: Add revision mode option (#286)

## v0.52.2 (2024-05-27)

### Fix

- **ContainerApp**: Add explicit from_public_registry option for container images (#285)

## v0.52.1 (2024-05-27)

### Fix

- **StorageAccount**: Turn on strict schema for app permissions model (no additional fields allowed) (#283)

## v0.52.0 (2024-05-27)

### Feat

- **app_workload**: Add support for stack references in configurations (#282)

## v0.51.1 (2024-05-27)

### Fix

- **AzureResourceId**: Make Azure resource ID validation case insensitive (#281)

## v0.51.0 (2024-05-27)

### Feat

- **StorageAccount**: Add blob containers (#280)

## v0.50.0 (2024-05-27)

### Feat

- **EventHub**: Improve namespace and hub output (#279)

## v0.49.0 (2024-05-27)

### Feat

- **EventGridDomain**: Add topics and endpoint to outputs (#278)

## v0.48.0 (2024-05-27)

### BREAKING CHANGE

- partition_count renamed to partitions, strict validation applied (no extra fields allowed)

### Fix

- **EventHub**: EventHubSchema clarifications (#277)

## v0.47.5 (2024-05-23)

### Fix

- **ContainerApp**: Add optional explicit name for cases when multiple apps are being deployed (#275)

## v0.47.4 (2024-05-23)

### Fix

- **stack_schema**: Fix azuread:tenantId not allowed warning in yaml schema (#271)

## v0.47.3 (2024-04-30)

### Fix

- **ora_queue**: had a bug regarding display of available tables in specified Environment (#255)

## v0.47.2 (2024-04-29)

### Fix

- Adding Todo list of things to fix within project before deploying it to customers

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

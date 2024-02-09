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

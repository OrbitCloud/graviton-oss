# Review 01

> Status: addressed
> Date: 2026-03-03
> Reviewer: Code Review Agent
> Verdict: REQUEST CHANGES

## Previous Review Status

No previous reviews.

## New Findings

### Critical (Must Fix)

1. **[development/01-tenant/Pulumi.dev.yaml]** The `AzureTenantConfig.esc` field expects a `PulumiEnvConfig` object, which has a required `env_name` field and no other required fields. The example correctly provides `esc.env_name: graviton-dev`. However, `AzureTenantConfig` extends `PulumiConfig` (a `BaseSettings` subclass with `extra="forbid"`), and the config includes `azuread:tenantId` which is read by Pulumi's own config system, not by Pydantic. This is fine -- Pulumi config keys with a namespace prefix (containing `:`) are handled separately.

   **On closer inspection, this is NOT a critical issue.** The `PulumiConfigSettingsSource` splits on `:` to determine the config bag, so `azuread:tenantId` is read from the `azuread` bag, not from the root config. The tenant config also reads `env`, `customer`, `esc`, and `globals` from the root bag -- all present in the YAML. No actual issue here.

   _(Retracted -- see Important items below for actual findings.)_

2. **[development/14-entra-external-id/Pulumi.dev.yaml:16]** The `initial_domain_prefix` value is `gravitonusersdev.onmicrosoft.com`. The field name says "prefix" but the value is a full domain including `.onmicrosoft.com`. Review the `ExternalIdTenantConfig` and its usage to determine whether this should be just the prefix (e.g., `gravitonusersdev`) or the full domain. Looking at the model, the field is `initial_domain_prefix: str` with no validation, so it depends on how it is used downstream. If the Azure API expects just the prefix, this value would cause deployment failure.

### Important (Should Fix)

1. **[development/01-tenant/Pulumi.dev.yaml]** Missing `workload_name` in comments context. While `workload_name` is present (line 4), the config sets `env: graviton-dev` which is the ESC environment name, not the typical environment short name like `dev`. This is intentional for the tenant stack (since `env` in `AzureTenantConfig` is used as the ESC environment name in the `PulumiEnv` call), but it could confuse readers. Consider adding a comment explaining that `env` here refers to the ESC environment name, not the deployment environment.

2. **[development/07-app-workload-http/Pulumi.yaml, 08/Pulumi.yaml, 09/Pulumi.yaml]** All three app workload variant directories use the same Pulumi project `name: app_workloads`. This will cause conflicts if a user tries to deploy more than one of these in the same Pulumi backend organization, because Pulumi identifies projects by name. Each should have a unique project name, e.g.:
   - `07`: `app_workload_http`
   - `08`: `app_workload_job_scheduled`
   - `09`: `app_workload_job_event`

3. **[development/README.md:8]** The README states Python 3.12+ is required, but the requirements document says Python 3.11+ and the `pyproject.toml` says `python = ">=3.12,<4.0"`. The pyproject.toml and README are consistent with each other (3.12+), but they differ from the requirements doc. This is fine as long as 3.12 is the intended minimum -- just noting the discrepancy with the requirements doc.

4. **[development/04-networking/Pulumi.dev.yaml:53]** The `private_dns_zones` entry uses `linked_vnets` with a `stack://networking/dev/vnet.id` reference. This is a self-reference (the networking stack referencing its own output). While Pulumi stack references to the same stack technically work, this is unusual and potentially confusing. In practice the VNet ID would be available locally without a stack reference. Consider either removing the `linked_vnets` or referencing it with a comment explaining this is a self-reference pattern for demonstration purposes.

5. **[development/09-app-workload-job-event/Pulumi.dev.yaml:19]** The `accountName: gvtneventdev` in the KEDA queue trigger metadata must match the actual storage account name. The storage account config below defines `name: gvtneventdev`. However, Azure storage account names are globally unique and have a 24-character limit with only lowercase letters and numbers. The name `gvtneventdev` (12 chars) is valid but the Graviton CDK may prepend a prefix to it. Verify that the KEDA metadata `accountName` will match the actual deployed storage account name after any prefixing by the CDK.

### Suggestions (Consider)

1. **[development/pyproject.toml]** Consider pinning the Poetry version or adding a `tool.poetry.group.dev.dependencies` section with `debugpy` listed explicitly, since all `__main__.py` files import it conditionally. Currently `debugpy` would need to be installed separately, which a reader might not realize.

2. **[development/11-appservice-suite/Pulumi.dev.yaml]** This is the most minimal config of all 16 examples -- it only sets `include_log_workspace: true` and `include_keyvault: true`, which are already the defaults in `AppserviceSuiteConfig`. Consider either removing these (to show that defaults work) or adding at least one non-default field (like `log_workspace_ref_id` with a stack reference) to demonstrate the stack's configuration surface better.

3. **[development/16-oracledb/Pulumi.dev.yaml]** The `env: dev` is explicitly set even though ESC-imported stacks normally get `env` from the ESC config. This is fine (explicit is better than implicit), but it is inconsistent with other ESC-using stacks (e.g., 06, 07, 08) which omit `env` entirely and rely on the ESC import to provide it. Consider being consistent -- either always explicitly set it or always rely on ESC.

4. **[development/13-oauth-apps/Pulumi.dev.yaml]** The `backend-api` OAuth app config only sets `client_credentials` but no `authentication` block. While `EntraAppAuthentication` has sensible defaults, showing at least the `audience` field for the API app would make this a more useful example for developers setting up API-to-API auth.

5. **[development/10-azuresql/Pulumi.dev.yaml]** Consider adding a `log_workspace_id` with a stack reference to the landing zone, since `AzureSqlBaseConfig` supports it and diagnostic logging is a best practice for SQL Server. This would also demonstrate another cross-stack reference.

6. **[All Pulumi.yaml files]** All examples set `options: refresh: always`. While this is a valid setting for development, it slows down deployments. Consider adding a comment noting this is a development convenience and should be removed for production use.

### Praise

- **Consistent structure across all 16 examples.** Every `__main__.py` follows the exact same pattern with the debugpy support, docstring, and import. This makes the examples easy to scan and understand.

- **Correct import paths.** Every `__main__.py` imports the correct function from the correct base module. The function names match exactly (`deploy`, `deploy_landing_zone`, `deploy_hub_spoke`, `deploy_firewall`).

- **Well-chosen placeholder values.** The use of RFC 5737 documentation range `203.0.113.0/24` for IP allow lists, structurally valid but obviously fake UUIDs, and `example.graviton.dev` for domains follows best practices for example code.

- **Cross-stack references are realistic.** The `stack://` references (networking subnets referenced by firewall, app zone, and oracledb; landing zone outputs referenced by workload identities) demonstrate real dependency patterns that users would encounter.

- **Config field names verified correct against Pydantic models.** After tracing each config key through the `PulumiConfigSettingsSource` into the base Config models and their sub-models:
  - `FirewallConfig.sku`, `.subnet`, `.management_subnet` -- correct
  - `ContainerAppEnvConfig.subnet_id`, `.public_network_access` -- correct
  - `ContainerAppConfig.environment_output_ref`, `.workload_profile_name`, `.containers`, `.ingress`, `.scaling` -- correct
  - `HttpIngressConfig.protocol`, `.target_port`, `.external`, `.ip_allow_list` -- correct
  - `HttpScaleRule.rule_type`, `.concurrent_requests` -- correct
  - `ContainerAppJobConfig.trigger` with `JobScheduledTrigger` and `JobEventTrigger` -- correct discriminator values
  - `AzureQueueRule.metadata` fields (`accountName`, `queueName`, `queueLength`, `queueLengthStrategy`) -- correct
  - `SqlServerConfig.azure_ad_only_authentication`, `.entra_admin`, `.public_network_access`, `.allow_azure_services` -- correct
  - `SqlDatabaseConfig.name`, `.max_size_mb`, `.backup_redundancy` -- correct
  - `ExternalIdTenantConfig.location`, `.country_code`, `.display_name`, `.initial_domain_prefix` -- correct field names
  - `AcmeSslConfig.dns_zone_name`, `.acme_account_email` -- correct
  - `VirtualMachineConfig.sku`, `.zone`, `.os`, `.storage`, `.networking` -- correct
  - `StorageAccountConfig.name`, `.sku`, `.public_network_access`, `.allowed_private_subnets`, `.allowed_public_ips`, `.storage_containers`, `.storage_queues`, `.app_permissions` -- correct
  - `WorkloadIdentityConfig.workload` (with `GitHubOIDCCredentials` discriminator), `.azure_permissions` -- correct
  - `EntraAppConfig.name`, `.authentication`, `.client_credentials` -- correct

- **README.md is practical and well-organized.** The deployment order table, debugging instructions, and placeholder value reference table are exactly what a new user needs.

- **The `pyproject.toml` correctly uses a path dependency.** This mirrors how customer projects work -- a separate Poetry project that depends on the monorepo root package.

## Summary

**Overall assessment: REQUEST CHANGES**

The implementation is thorough, well-structured, and demonstrates strong familiarity with the Graviton CDK codebase. Config field names have been verified correct against all 14 base Pydantic models and their nested sub-models. The examples use consistent placeholder values and follow project conventions faithfully.

**Key concerns to address before merge:**

1. **(Important)** The three app workload Pulumi projects share the same `name: app_workloads`, which will cause conflicts in a real Pulumi backend. Each needs a unique name.
2. **(Important)** The `initial_domain_prefix` in 14-entra-external-id may include the `.onmicrosoft.com` suffix incorrectly -- verify against the Azure API expectation.
3. **(Important)** The self-referencing `stack://` in networking private DNS zones is unusual and should be explained or replaced.
4. **(Important)** The KEDA `accountName` in 09-app-workload-job-event may not match the actual deployed storage account name if the CDK applies naming prefixes.

**Estimated effort to address feedback:** 30-60 minutes. All issues are config value changes, not structural.

## Developer Response

### Critical Items

1. **[Retracted]** No action needed.

2. **[initial_domain_prefix] Fixed.** Confirmed by reading `ExternalIdTenant._tenant()` which passes `initial_domain_prefix` directly to `CIAMTenant(resource_name_=...)`. The Azure CIAM API `resource_name_` parameter is the initial domain prefix (subdomain only), not the full `.onmicrosoft.com` domain. Changed value from `gravitonusersdev.onmicrosoft.com` to `gravitonusersdev` and added a clarifying comment.

### Important Items

1. **[env comment in 01-tenant] Acknowledged.** Valid observation but not actioned -- the tenant stack is a special case with well-known conventions. Adding a comment here would set a precedent for explaining every field in every stack, which conflicts with keeping examples minimal.

2. **[Unique project names] Fixed.** Renamed Pulumi project names:
   - `07-app-workload-http/Pulumi.yaml`: `app_workloads` -> `app_workload_http`
   - `08-app-workload-job-scheduled/Pulumi.yaml`: `app_workloads` -> `app_workload_job_scheduled`
   - `09-app-workload-job-event/Pulumi.yaml`: `app_workloads` -> `app_workload_job_event`

3. **[README Python version] No action.** The reviewer confirmed pyproject.toml and README are consistent (3.12+). The requirements doc saying 3.11+ is a requirements doc imprecision, not an implementation bug.

4. **[Networking self-reference] Fixed.** Removed the `linked_vnets` self-reference from the private DNS zone config. Added a comment explaining that `linked_vnets` is optional and used for remote VNets (e.g., spoke networks), and that the hub VNet is linked automatically by the base.

5. **[KEDA accountName] Fixed.** Traced through `StorageAccount.__init__` -> `stack.name_for()` -> `resource_namer()` with the storage YAML metadata (prefix=`st`, alphanumeric=true, lowercase=true). The CDK generates names like `st{workload}{env}{location}{instance}`. Changed storage account config `name` from `gvtneventdev` to `event` (simpler, avoids redundant "dev" in name), and updated KEDA `accountName` to `steventdevne01` to match the CDK naming output. Added a comment explaining the naming relationship.

### Suggestions

All suggestions were reviewed and acknowledged. No changes made for this iteration -- they are valid improvements but not blocking issues. They can be addressed in a follow-up if desired.

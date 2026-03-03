# Stack Examples - Implementation Summary

## What was implemented

Created 16 example Pulumi project directories under `development/`, plus shared configuration files, covering all 14 Graviton CDK base stack types (with 3 app workload variants).

### Shared files
- `development/pyproject.toml` -- Poetry config with `orbitcloud-graviton` as a path dependency to the monorepo root
- `development/README.md` -- Documentation covering prerequisites, placeholder values, deployment order, debugging, and schema validation

### Example directories (16 total)

Each directory contains `Pulumi.yaml`, `Pulumi.dev.yaml`, and `__main__.py`:

| # | Directory | Base | Key Config |
|---|-----------|------|------------|
| 01 | `01-tenant` | `azure_tenant` | Customer info, ESC env, global tags, IP allow list |
| 02 | `02-environment` | `azure_environment` | ESC OIDC credentials, subscription binding, imports |
| 03 | `03-landing-zone` | `landing_zone` | Key Vault, Container Registry, DNS zone, ACME SSL |
| 04 | `04-networking` | `hubspoke` | VNet with 6 subnets (apps, psql, firewall, gateway), DNS zones |
| 05 | `05-firewall` | `firewall` | Basic SKU with management subnet, log analytics |
| 06 | `06-app-zone` | `app_zone` | Container App Environment on apps subnet, Key Vault |
| 07 | `07-app-workload-http` | `app_workload` | HTTP Container App with ingress and scaling rules |
| 08 | `08-app-workload-job-scheduled` | `app_workload` | Cron-triggered Container App Job |
| 09 | `09-app-workload-job-event` | `app_workload` | Queue-triggered Container App Job with storage account |
| 10 | `10-azuresql` | `azuresql` | SQL Server with Entra-only auth and sample database |
| 11 | `11-appservice-suite` | `appservice_suite` | App Service Plan with Log Analytics and Key Vault |
| 12 | `12-workload-identities` | `workload_identities` | GitHub Actions OIDC federation with Azure permissions |
| 13 | `13-oauth-apps` | `oauth_apps` | SPA and backend API app registrations |
| 14 | `14-entra-external-id` | `entra_external_id` | B2C tenant for customer-facing auth |
| 15 | `15-acme-ssl` | `acme_ssl` | Let's Encrypt wildcard certificate via Azure DNS |
| 16 | `16-oracledb` | `oracledb` | Oracle Linux VM with data disks and backup storage |

## Tests added

None -- these are configuration/example files, not library code. The examples are validated by `make fmt && make lint` passing.

## Design decisions and trade-offs

1. **`__main__.py` pattern**: Every example uses the `PULUMI_DEBUG` / debugpy pattern from real customer projects, matching the convention in `~/src/customer-infra-projects/`.

2. **Config derived from source code**: Each `Pulumi.dev.yaml` was written by reading the actual Pydantic `Config` models in each base, ensuring field names and types are correct. Customer project configs were used as reference for realistic values.

3. **Placeholder values**: All examples use the placeholder convention from the requirements (tenant `00000000...`, subscription `11111111...`, IP `203.0.113.0/24`). No real customer values are present.

4. **Cross-stack references**: Where stacks naturally depend on each other, `stack://` references are used (e.g., networking subnets referenced by firewall, app zone, and app workloads).

5. **ESC environment pattern**: Stacks that would normally inherit config from Pulumi ESC use `environment: [graviton-dev]`. The tenant stack does not use an ESC import (it creates the ESC environment). The `14-entra-external-id` example documents that it cannot use ESC OIDC due to Azure API limitations.

6. **Minimal but realistic**: Each config includes all required fields and a representative sample of optional fields -- enough to demonstrate the stack pattern without overwhelming the reader.

## Issues encountered

- The worktree did not have `poetry install` run yet, so `make fmt` initially failed. After `poetry install`, all validation passed cleanly.

## Review 01 changes

Addressed 4 issues from code review:

1. **Unique project names** -- Renamed `Pulumi.yaml` project names for the three app workload variants from the shared `app_workloads` to `app_workload_http`, `app_workload_job_scheduled`, and `app_workload_job_event` to avoid Pulumi backend conflicts.

2. **initial_domain_prefix** -- Fixed `14-entra-external-id/Pulumi.dev.yaml` to use just the prefix (`gravitonusersdev`) instead of the full domain (`gravitonusersdev.onmicrosoft.com`). The Azure CIAM API expects only the subdomain prefix.

3. **Networking self-reference** -- Removed the `linked_vnets: [stack://networking/dev/vnet.id]` self-reference from `04-networking/Pulumi.dev.yaml`. Added a comment explaining that `linked_vnets` is for remote VNets and the hub VNet is linked automatically by the base.

4. **KEDA accountName** -- Fixed `09-app-workload-job-event/Pulumi.dev.yaml` to use the CDK-generated storage account name (`steventdevne01`) instead of the config input name. Simplified storage account config `name` from `gvtneventdev` to `event`. Added a comment explaining the CDK naming convention.

## Suggested next steps

1. **Deploy and validate**: Run `pulumi preview` for each stack against a test Azure subscription to verify config parsing works end-to-end.
2. **P2 items**: Add a GitHub Actions workflow and deployment ordering script as described in the requirements.
3. **Schema generation**: Run each stack once to generate `.stack_schema.json` files for IDE autocompletion support.

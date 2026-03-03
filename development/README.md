# Graviton CDK - Example Stacks

This directory contains example Pulumi stacks demonstrating every stack type available
in the Graviton CDK. These serve as both documentation and integration test targets.

## Prerequisites

- Python 3.12+
- [Poetry](https://python-poetry.org/) installed
- [Pulumi CLI](https://www.pulumi.com/docs/install/) installed
- Azure CLI (`az login`) with an active session
- A Pulumi account and organization

## Setup

```bash
cd development/
poetry install
```

## Placeholder Values

All examples use placeholder values that must be replaced before deployment:

| Value | Placeholder | Replace With |
|-------|------------|--------------|
| Tenant ID | `00000000-0000-0000-0000-000000000000` | Your Azure AD tenant ID |
| Subscription ID | `11111111-1111-1111-1111-111111111111` | Your Azure subscription ID |
| Location | `northeurope` | Your preferred Azure region |
| ESC Environment | `graviton-dev` | Your Pulumi ESC environment name |
| IP allow list | `203.0.113.0/24` | Your office/VPN IP range |
| Domain name | `example.graviton.dev` | Your DNS domain |

## Deployment Order

Stacks should be deployed in numerical order, as later stacks may reference
outputs from earlier ones via `stack://` references.

```
01-tenant          # Azure Tenant configuration (Pulumi ESC)
02-environment     # Azure Environment (Pulumi ESC OIDC credentials)
03-landing-zone    # Log Analytics, Key Vault, Container Registry
04-networking      # Hub-Spoke Virtual Network
05-firewall        # Azure Firewall (requires networking subnets)
06-app-zone        # Container App Environment, Key Vault, App Insights
07-app-workload-http           # HTTP-triggered Container App
08-app-workload-job-scheduled  # Scheduled (cron) Container App Job
09-app-workload-job-event      # Event-driven Container App Job (queue trigger)
10-azuresql        # Azure SQL Server + Database
11-appservice-suite # App Service Plan
12-workload-identities # Federated credentials for CI/CD
13-oauth-apps      # OAuth/OIDC app registrations
14-entra-external-id # Entra External ID (B2C) tenant
15-acme-ssl        # Let's Encrypt ACME wildcard certificates
16-oracledb        # Oracle Database on Azure VM
```

## Deploying a Single Stack

```bash
cd 07-app-workload-http/
pulumi up --stack dev
```

## Debugging

Each `__main__.py` includes support for the `PULUMI_DEBUG` environment variable.
Set it to `true` to enable debugpy on port 5678:

```bash
PULUMI_DEBUG=true pulumi up --stack dev
```

Then attach your IDE debugger to `localhost:5678`.

## Schema Validation

Each `Pulumi.dev.yaml` includes a `yaml-language-server` schema reference.
Run `pulumi preview` once to generate the `.stack_schema.json` file, then
your IDE will provide autocompletion and validation for the config values.

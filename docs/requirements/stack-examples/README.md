# Stack Examples Requirements

## Overview

Create a comprehensive set of example Pulumi stacks in the `development/` folder that demonstrate how to configure and deploy every stack type available in Graviton. These examples serve two purposes:

1. **Documentation/Demonstration** — Show developers how to configure each stack type with realistic, well-commented configurations
2. **Integration Testing** — Provide deployable stacks that can be run against a real Azure subscription to validate the Graviton CDK

## Goals

- Cover all 14 stack types with at least one working example each
- Use placeholder Azure tenant/subscription values (to be replaced with real values when deploying)
- Follow existing project conventions (Copier template patterns, schema generation, debug support)
- Keep examples minimal but realistic — enough config to demonstrate the stack, not so much that it obscures the pattern
- Each example should be independently deployable via `pulumi up`

## User Stories

- As a **new Graviton user**, I want to see working examples of every stack type so that I can understand how to configure my own infrastructure
- As a **Graviton contributor**, I want to run example stacks against Azure so that I can validate changes don't break real deployments
- As a **platform engineer**, I want reference configurations I can copy and adapt for new customer projects

## Directory Structure

```
development/
├── pyproject.toml                    # Shared Python/Poetry config for all examples
├── poetry.lock
├── README.md                         # Overview and usage instructions
│
├── 01-tenant/                        # Azure Tenant configuration
│   ├── Pulumi.yaml
│   ├── Pulumi.dev.yaml
│   └── __main__.py
│
├── 02-environment/                   # Azure Environment (Pulumi ESC)
│   ├── Pulumi.yaml
│   ├── Pulumi.dev.yaml
│   └── __main__.py
│
├── 03-landing-zone/                  # Landing Zone (Log Analytics, Key Vault, etc.)
│   ├── Pulumi.yaml
│   ├── Pulumi.dev.yaml
│   └── __main__.py
│
├── 04-networking/                    # Hub-Spoke Network
│   ├── Pulumi.yaml
│   ├── Pulumi.dev.yaml
│   └── __main__.py
│
├── 05-firewall/                      # Azure Firewall
│   ├── Pulumi.yaml
│   ├── Pulumi.dev.yaml
│   └── __main__.py
│
├── 06-app-zone/                      # Container App Environment
│   ├── Pulumi.yaml
│   ├── Pulumi.dev.yaml
│   └── __main__.py
│
├── 07-app-workload-http/             # App Workload — HTTP-triggered container app
│   ├── Pulumi.yaml
│   ├── Pulumi.dev.yaml
│   └── __main__.py
│
├── 08-app-workload-job-scheduled/    # App Workload — Scheduled (cron) job
│   ├── Pulumi.yaml
│   ├── Pulumi.dev.yaml
│   └── __main__.py
│
├── 09-app-workload-job-event/        # App Workload — Event-driven job (queue/blob trigger)
│   ├── Pulumi.yaml
│   ├── Pulumi.dev.yaml
│   └── __main__.py
│
├── 10-azuresql/                      # Azure SQL Server + Database
│   ├── Pulumi.yaml
│   ├── Pulumi.dev.yaml
│   └── __main__.py
│
├── 11-appservice-suite/              # App Service Plan
│   ├── Pulumi.yaml
│   ├── Pulumi.dev.yaml
│   └── __main__.py
│
├── 12-workload-identities/           # Federated credentials for CI/CD
│   ├── Pulumi.yaml
│   ├── Pulumi.dev.yaml
│   └── __main__.py
│
├── 13-oauth-apps/                    # OAuth/OIDC app registrations
│   ├── Pulumi.yaml
│   ├── Pulumi.dev.yaml
│   └── __main__.py
│
├── 14-entra-external-id/             # Entra External ID (B2C)
│   ├── Pulumi.yaml
│   ├── Pulumi.dev.yaml
│   └── __main__.py
│
├── 15-acme-ssl/                      # Let's Encrypt ACME certificates
│   ├── Pulumi.yaml
│   ├── Pulumi.dev.yaml
│   └── __main__.py
│
└── 16-oracledb/                      # Oracle DB on Azure VM
    ├── Pulumi.yaml
    ├── Pulumi.dev.yaml
    └── __main__.py
```

**Numbering rationale:** Numbers reflect a natural deployment order (tenant first, then environment, then landing zone, networking, etc.). App workloads are split into 3 variants (HTTP, scheduled job, event-driven job) as requested — one example per distinct workload pattern.

## Functional Requirements

### Must Have (P0)

- [ ] **All 14 stack types covered** — One example directory per base, plus 3 app workload variants (16 total)
- [ ] **Standard project structure per example** — Each directory contains `Pulumi.yaml`, `Pulumi.dev.yaml`, and `__main__.py` following the Copier template pattern
- [ ] **Placeholder Azure values** — Use clearly fake but structurally valid UUIDs for tenant/subscription IDs (e.g., `00000000-0000-0000-0000-000000000000`)
- [ ] **Schema validation support** — Each `Pulumi.dev.yaml` includes `# yaml-language-server: $schema=.stack_schema.json` header
- [ ] **Minimal but complete configs** — Each stack config includes all required fields and a representative sample of optional fields to demonstrate capabilities
- [ ] **Debug support** — Each `__main__.py` includes the standard `PULUMI_DEBUG` / debugpy pattern used in customer projects
- [ ] **Shared pyproject.toml** — Single Poetry config at `development/` root with `orbitcloud_graviton` as a path dependency
- [ ] **README.md at root** — Documents the purpose, prerequisites, and how to deploy each example

### Should Have (P1)

- [ ] **Comments in config files** — Brief inline comments in `Pulumi.dev.yaml` explaining what key config values do
- [ ] **Cross-stack references** — Where stacks naturally reference each other (e.g., app-workload referencing app-zone), use `stack://` reference syntax to demonstrate the pattern
- [ ] **Realistic resource naming** — Use a consistent naming convention (e.g., `graviton-dev` prefix) that mirrors real-world patterns

### Nice to Have (P2)

- [ ] **CI/CD integration** — GitHub Actions workflow to deploy/destroy examples against a test subscription
- [ ] **Deployment ordering script** — Simple script that deploys all stacks in dependency order

## Non-Functional Requirements

- **Security:** No real secrets, tenant IDs, subscription IDs, IP addresses, or customer-specific values committed. All sensitive values must be clearly placeholder.
- **Backwards Compatibility:** Not applicable (new directory, no existing code affected)
- **Maintainability:** Examples should import and call the base `deploy()` functions directly — no custom Pulumi resource code in examples. When a base changes, examples automatically reflect it.

## Placeholder Values Convention

Use these consistent placeholder values across all examples:

| Value | Placeholder |
|-------|------------|
| Tenant ID | `00000000-0000-0000-0000-000000000000` |
| Subscription ID | `11111111-1111-1111-1111-111111111111` |
| Location | `northeurope` |
| Environment | `dev` |
| ESC Environment | `graviton-dev` |
| Workload prefix | `gvtn` (short for graviton) |
| IP allow list | `203.0.113.0/24` (RFC 5737 documentation range) |
| SSH public key | `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExample... example@graviton` |
| Domain name | `example.graviton.dev` |
| VNet address space | `10.200.0.0/16` |
| Subnet prefixes | `10.200.x.0/24` |

## Edge Cases & Error Handling

| Scenario | Expected Behavior |
|----------|-------------------|
| `pulumi preview` with placeholder values | Should succeed structurally (schema validation passes) even without real Azure credentials |
| Missing ESC environment | Stacks that reference ESC should document this dependency clearly in comments |
| Cross-stack references to non-existent stacks | Should be documented with comments explaining which stack must be deployed first |
| Oracle DB cloud-init | Should include a minimal cloud-init template without real Oracle licenses or proprietary config |

## Affected Components/Bases

No modifications to existing bases or components. This creates **new content only** under `development/`.

All 14 bases are consumed (read-only) by the examples:
- `bases/orbitcloud_graviton/azure_tenant/`
- `bases/orbitcloud_graviton/azure_environment/`
- `bases/orbitcloud_graviton/landing_zone/`
- `bases/orbitcloud_graviton/hubspoke/`
- `bases/orbitcloud_graviton/firewall/`
- `bases/orbitcloud_graviton/app_zone/`
- `bases/orbitcloud_graviton/app_workload/`
- `bases/orbitcloud_graviton/azuresql/`
- `bases/orbitcloud_graviton/appservice_suite/`
- `bases/orbitcloud_graviton/workload_identities/`
- `bases/orbitcloud_graviton/oauth_apps/`
- `bases/orbitcloud_graviton/entra_external_id/`
- `bases/orbitcloud_graviton/acme_ssl/`
- `bases/orbitcloud_graviton/oracledb/`

## Out of Scope

- Modifying any existing base or component code
- Creating new Pulumi components or bases
- Real Azure deployments (that's a follow-up activity using these examples)
- Pulumi ESC environment setup (documented as a prerequisite)
- CI/CD pipeline implementation (P2 nice-to-have, separate effort)

## Dependencies

- All 14 Graviton bases must be importable (they already exist)
- Python 3.11+ with Poetry
- Pulumi CLI installed
- For actual deployment: Azure subscription, Pulumi ESC environment, and `az login` session

## Open Questions

- [ ] Should the `development/` folder share the repo-root `pyproject.toml` or have its own? (Recommendation: own `pyproject.toml` with path dependency on `orbitcloud_graviton` to mirror how customer projects work)
- [ ] Do we want multiple stack variants per example (e.g., `Pulumi.dev.yaml` AND `Pulumi.prod.yaml`) or just `dev`? (Recommendation: just `dev` to keep it simple)

## Acceptance Criteria

1. All 16 example directories exist under `development/` with the correct file structure
2. Each `__main__.py` imports from the correct base and calls `deploy()`
3. Each `Pulumi.dev.yaml` contains valid configuration for its stack type with placeholder values
4. No real customer-specific values (tenant IDs, subscription IDs, names, IPs) are present
5. `development/README.md` documents prerequisites and deployment order
6. `pyproject.toml` at `development/` root has `orbitcloud_graviton` as a dependency
7. `pulumi preview` succeeds structurally for each stack (schema validation, config parsing) when run with appropriate Azure credentials

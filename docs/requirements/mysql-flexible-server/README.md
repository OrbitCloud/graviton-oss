# MySQL Flexible Server Component Requirements

## Overview

New Graviton CDK component for provisioning Azure Database for MySQL Flexible Server. Follows the established PostgreSQL Flexible Server pattern (`az_postgres`) with additions for firewall rules (from `az_sql` pattern) and MySQL-specific database resources.

Default posture: private VNet integration, system-assigned identity, Entra authentication enabled, MySQL 8.4.

## Goals

- Provide a reusable, opinionated MySQL Flexible Server component consistent with existing Graviton patterns
- Default to secure-by-default networking (VNet integration, public access disabled)
- Support Entra ID authentication with system-assigned managed identity
- Allow optional IP allowlisting for hybrid scenarios
- Support creating databases on the server

## User Stories

- As a platform engineer, I want to deploy a MySQL Flexible Server into my landing zone VNet so that database traffic stays private.
- As a platform engineer, I want Entra authentication enabled by default so that I can use managed identities for access.
- As a platform engineer, I want to create databases on the server so that application teams have their schemas ready.
- As a platform engineer, I want to optionally allowlist public IPs so that I can support hybrid connectivity scenarios.

## Functional Requirements

### Must Have (P0)

- [ ] **Server resource** — `MysqlFlexibleServer` ComponentResource creating `dbformysql.Server`
  - Default version: `"8.4"` (passed as string; SDK enum lags behind Azure API)
  - Default SKU: `Standard_B1ms` / `Burstable` tier
  - System-assigned identity via `identity` arg (note: MySQL SDK uses `ManagedServiceIdentityType.USER_ASSIGNED` enum but system-assigned is set differently — verify at implementation)
  - Data encryption: system-managed
  - Replication role: `None` (standalone)
  - Create mode: `Default` (with support for `PointInTimeRestore`, `GeoRestore`, `Replica`)

- [ ] **Entra authentication** — `dbformysql.AzureAdAdministrator` resource
  - Enabled by default
  - Registers the Pulumi ESC app service principal as admin (matching PostgreSQL pattern)
  - Config option to supply additional Entra admin object IDs

- [ ] **Authentication config** — `MysqlAuthConfig` model
  - `admin_username: str = "cloudsa"`
  - `admin_password: str | None = None` (auto-generated via `random.RandomPassword` if not provided)
  - `entra_auth: bool = True`
  - `mysql_auth: bool = True` (native MySQL password auth toggle)

- [ ] **Networking** — `MysqlNetworkConfig` model
  - `subnet_id: AzureIdRef` — delegated subnet (`Microsoft.DBforMySQL/flexibleServers`)
  - `private_dns_zone_id: AzureIdRef` — private DNS zone for name resolution
  - Public network access: `Disabled` by default when VNet config is provided
  - Note: MySQL SDK uses `private_dns_zone_resource_id` (differs from PostgreSQL's `private_dns_zone_arm_resource_id`)

- [ ] **Firewall rules** — IP allowlisting (from `az_sql` pattern)
  - `allowed_public_networks: list[PublicIpv4FirewallRule] | None = None`
  - `allow_azure_services: bool = False`
  - Reuse `PublicIpv4FirewallRule` from `orbitcloud_graviton.az_network.types`
  - Public network access set to `Enabled` when firewall rules are configured
  - Validation: firewall rules and VNet integration are mutually exclusive

- [ ] **Database resources** — `MysqlDatabaseConfig` model + creation
  - `name: str`
  - `charset: str = "utf8mb4"`
  - `collation: str = "utf8mb4_unicode_ci"`
  - Config field: `databases: list[MysqlDatabaseConfig] | None = None`
  - Creates `dbformysql.Database` resources parented to the server

- [ ] **Storage config** — `MysqlStorageConfig` model
  - `storage_size_gb: int = 32`
  - `auto_grow: EnableStatusEnum = DISABLED`
  - `auto_io_scaling: EnableStatusEnum = ENABLED`
  - `iops: int | None = None`

- [ ] **Backup config** — `MysqlBackupConfig` model
  - `geo_redundant: EnableStatusEnum = DISABLED`
  - `retention_days: int = 7`

- [ ] **Server parameters** — `server_params: dict[str, str] | None = None`
  - Creates `dbformysql.Configuration` resources per parameter
  - Source: `user-override`

- [ ] **Diagnostic settings** — conditional, using shared `diagnostic_setting()` helper
  - Log categories: MySQL-appropriate categories (e.g., `MySqlAuditLogs`, `MySqlSlowLogs`)
  - Metric category: `AllMetrics`

- [ ] **Stack outputs** — export server id, name, FQDN, admin credentials

### Should Have (P1)

- [ ] **High Availability** — `MysqlHAConfig` model
  - `mode: HighAvailabilityMode = DISABLED`
  - `standby_availability_zone: str | None = None`
  - Support `ZoneRedundant` and `SameZone` modes

- [ ] **Maintenance window** — `MysqlMaintenanceConfig` model
  - `day_of_week: int = 0`
  - `start_hour: int = 0`
  - `start_minute: int = 0`

- [ ] **SKU config** — `MysqlSku` model
  - `name: str = "Standard_B1ms"`
  - `tier: ServerSkuTier = BURSTABLE`

### Nice to Have (P2)

- [ ] **Create mode support** — `MysqlCreateMode` model
  - `mode: CreateMode = DEFAULT`
  - `source_server_id: str | None = None` (required for restore/replica)
  - `restore_point_in_time: str | None = None` (required for PITR)
  - Cross-field validation via `model_validator`

## Non-Functional Requirements

- **Naming**: Use `stack.name_for()` with prefixes from `dbformysql.yaml` metadata
- **Config validation**: Pydantic `BaseModel` with `extra="forbid"`, `arbitrary_types_allowed=True`
- **Security**: No secrets in plain text; admin password auto-generated if not supplied
- **Backwards Compatibility**: N/A — new component, no existing users
- **Testing**: Unit tests using `pulumi_mocks` following existing test patterns

## Edge Cases & Error Handling

| Scenario | Expected Behavior |
|----------|-------------------|
| VNet config + firewall rules both provided | Pydantic validation error — mutually exclusive |
| Firewall rules without VNet config | Public access enabled, rules created |
| No VNet config and no firewall rules | Public access enabled, no rules (open — user's choice) |
| No admin password provided | Auto-generate via `random.RandomPassword` |
| Entra auth disabled | Skip `AzureAdAdministrator` resource creation |
| Empty databases list | No `Database` resources created |
| HA mode set but Burstable SKU | Azure API will reject — document this constraint, no client-side validation |
| SDK lacks 8.4 enum | Pass `"8.4"` as string directly to `version` arg |

## Affected Components/Bases

### New (create)
- `components/orbitcloud_graviton/az_mysql/__init__.py`
- `components/orbitcloud_graviton/az_mysql/flexibleserver.py`
- `components/orbitcloud_graviton/az_lib/metadata/services/dbformysql.yaml`
- `test/components/orbitcloud_graviton/az_mysql/__init__.py`
- `test/components/orbitcloud_graviton/az_mysql/test_flexibleserver.py`

### Modified
- `pyproject.toml` — add `az_mysql` package entry

## Out of Scope

- Read replicas (cross-region or same-region)
- Customer-managed encryption keys (BYOK)
- Deployable base stack (`bases/` entry point) — can be added later
- Private Endpoint connectivity (component uses VNet injection; PE can be composed externally)
- Slow query log configuration beyond server params
- MySQL Single Server (legacy, deprecated)

## Dependencies

- `pulumi_azure_native.dbformysql` (v3.14.0+ installed)
- `pulumi_random` — for `RandomPassword`
- `orbitcloud_graviton.az_network.types.PublicIpv4FirewallRule`
- `orbitcloud_graviton.az_lib` — naming, metadata loader
- `orbitcloud_graviton.pulumi_lib` — `AzureStack`, `EntraStack`
- `orbitcloud_graviton.az_monitor` — `diagnostic_setting()` helper

## Open Questions

- [x] MySQL 8.4 not in SDK enum → pass as raw string ✓
- [ ] Confirm MySQL diagnostic log category names against Azure API docs
- [ ] Verify system-assigned identity support — MySQL SDK exposes `ManagedServiceIdentityType.USER_ASSIGNED` only; system-assigned may need to be set via a different mechanism or may not be supported for MySQL Flexible Server (fallback: user-assigned identity)

## Acceptance Criteria

- `MysqlFlexibleServer` component deploys a MySQL 8.4 Flexible Server with VNet integration
- Entra authentication is enabled by default with ESC app as admin
- Admin password is auto-generated when not provided
- Databases can be created on the server
- Firewall rules work when VNet integration is not used
- Validation prevents combining VNet integration with firewall rules
- All config models enforce `extra="forbid"`
- YAML metadata enables correct naming via `stack.name_for()`
- `pyproject.toml` includes the new package
- Unit tests pass covering config validation and resource creation

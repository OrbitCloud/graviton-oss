import pytest
from pulumi_azure_native.dbformysql import (
    CreateMode,
    EnableStatusEnum,
    HighAvailabilityMode,
    ServerSkuTier,
)

from orbitcloud_graviton.az_mysql.flexibleserver import (
    MysqlAuthConfig,
    MysqlBackupConfig,
    MysqlCreateMode,
    MysqlDatabaseConfig,
    MysqlFlexibleServerConfig,
    MysqlHAConfig,
    MysqlMaintenanceConfig,
    MysqlNetworkConfig,
    MysqlSku,
    MysqlStorageConfig,
)

# --- MysqlAuthConfig ---


def test_auth_config_defaults() -> None:
    config = MysqlAuthConfig()
    assert config.admin_username == "cloudsa"
    assert config.admin_password is None
    assert config.entra_auth is True


def test_auth_config_custom() -> None:
    config = MysqlAuthConfig(
        admin_username="myadmin",
        admin_password="secret123",  # NOSONAR - test credential
        entra_auth=False,
    )
    assert config.admin_username == "myadmin"
    assert config.admin_password == "secret123"
    assert config.entra_auth is False


def test_auth_config_forbids_extra() -> None:
    with pytest.raises(ValueError):
        MysqlAuthConfig.model_validate({"unknown_field": "value"})


# --- MysqlNetworkConfig ---


def test_network_config_valid() -> None:
    config = MysqlNetworkConfig(
        subnet_id="/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.Network/virtualNetworks/vnet/subnets/subnet",
        private_dns_zone_id="/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.Network/privateDnsZones/zone",
    )
    assert config.subnet_id is not None
    assert config.private_dns_zone_id is not None


def test_network_config_forbids_extra() -> None:
    with pytest.raises(ValueError):
        MysqlNetworkConfig.model_validate(
            {
                "subnet_id": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.Network/virtualNetworks/vnet/subnets/default",
                "private_dns_zone_id": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.Network/privateDnsZones/mysql.database.azure.com",
                "extra": "nope",
            }
        )


# --- MysqlStorageConfig ---


def test_storage_config_defaults() -> None:
    config = MysqlStorageConfig()
    assert config.storage_size_gb == 32
    assert config.auto_grow == EnableStatusEnum.DISABLED
    assert config.auto_io_scaling == EnableStatusEnum.ENABLED
    assert config.iops is None


def test_storage_config_custom() -> None:
    config = MysqlStorageConfig(
        storage_size_gb=128,
        auto_grow=EnableStatusEnum.ENABLED,
        auto_io_scaling=EnableStatusEnum.DISABLED,
        iops=5000,
    )
    assert config.storage_size_gb == 128
    assert config.iops == 5000


def test_storage_config_min_size() -> None:
    with pytest.raises(ValueError):
        MysqlStorageConfig(storage_size_gb=15)


def test_storage_config_max_size() -> None:
    with pytest.raises(ValueError):
        MysqlStorageConfig(storage_size_gb=100000)


def test_storage_config_forbids_extra() -> None:
    with pytest.raises(ValueError):
        MysqlStorageConfig.model_validate({"extra": "nope"})


# --- MysqlBackupConfig ---


def test_backup_config_defaults() -> None:
    config = MysqlBackupConfig()
    assert config.geo_redundant == EnableStatusEnum.DISABLED
    assert config.retention_days == 7


def test_backup_config_custom() -> None:
    config = MysqlBackupConfig(
        geo_redundant=EnableStatusEnum.ENABLED,
        retention_days=35,
    )
    assert config.geo_redundant == EnableStatusEnum.ENABLED
    assert config.retention_days == 35


def test_backup_config_forbids_extra() -> None:
    with pytest.raises(ValueError):
        MysqlBackupConfig.model_validate({"extra": "nope"})


# --- MysqlSku ---


def test_sku_defaults() -> None:
    config = MysqlSku()
    assert config.name == "Standard_B1ms"
    assert config.tier == ServerSkuTier.BURSTABLE


def test_sku_custom() -> None:
    config = MysqlSku(name="Standard_D2ds_v4", tier=ServerSkuTier.GENERAL_PURPOSE)
    assert config.name == "Standard_D2ds_v4"
    assert config.tier == ServerSkuTier.GENERAL_PURPOSE


def test_sku_forbids_extra() -> None:
    with pytest.raises(ValueError):
        MysqlSku.model_validate({"extra": "nope"})


# --- MysqlHAConfig ---


def test_ha_config_defaults() -> None:
    config = MysqlHAConfig()
    assert config.mode == HighAvailabilityMode.DISABLED
    assert config.standby_availability_zone is None


def test_ha_config_zone_redundant() -> None:
    config = MysqlHAConfig(
        mode=HighAvailabilityMode.ZONE_REDUNDANT,
        standby_availability_zone="2",
    )
    assert config.mode == HighAvailabilityMode.ZONE_REDUNDANT
    assert config.standby_availability_zone == "2"


def test_ha_config_forbids_extra() -> None:
    with pytest.raises(ValueError):
        MysqlHAConfig.model_validate({"extra": "nope"})


# --- MysqlMaintenanceConfig ---


def test_maintenance_config_defaults() -> None:
    config = MysqlMaintenanceConfig()
    assert config.day_of_week == 0
    assert config.start_hour == 0
    assert config.start_minute == 0


def test_maintenance_config_custom() -> None:
    config = MysqlMaintenanceConfig(day_of_week=3, start_hour=2, start_minute=30)
    assert config.day_of_week == 3


def test_maintenance_config_day_range() -> None:
    with pytest.raises(ValueError):
        MysqlMaintenanceConfig(day_of_week=7)


def test_maintenance_config_hour_range() -> None:
    with pytest.raises(ValueError):
        MysqlMaintenanceConfig(start_hour=24)


def test_maintenance_config_minute_range() -> None:
    with pytest.raises(ValueError):
        MysqlMaintenanceConfig(start_minute=60)


def test_maintenance_config_forbids_extra() -> None:
    with pytest.raises(ValueError):
        MysqlMaintenanceConfig.model_validate({"extra": "nope"})


# --- MysqlCreateMode ---


def test_create_mode_defaults() -> None:
    config = MysqlCreateMode()
    assert config.mode is None
    assert config.source_server_id is None
    assert config.restore_point_in_time is None


def test_create_mode_pitr_requires_source() -> None:
    with pytest.raises(ValueError, match="source_server_id is required"):
        MysqlCreateMode(mode=CreateMode.POINT_IN_TIME_RESTORE)


def test_create_mode_geo_restore_requires_source() -> None:
    with pytest.raises(ValueError, match="source_server_id is required"):
        MysqlCreateMode(mode=CreateMode.GEO_RESTORE)


def test_create_mode_replica_requires_source() -> None:
    with pytest.raises(ValueError, match="source_server_id is required"):
        MysqlCreateMode(mode=CreateMode.REPLICA)


def test_create_mode_pitr_requires_restore_time() -> None:
    with pytest.raises(ValueError, match="restore_point_in_time is required"):
        MysqlCreateMode(
            mode=CreateMode.POINT_IN_TIME_RESTORE,
            source_server_id="/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.DBforMySQL/flexibleServers/src",
        )


def test_create_mode_pitr_valid() -> None:
    config = MysqlCreateMode(
        mode=CreateMode.POINT_IN_TIME_RESTORE,
        source_server_id="/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.DBforMySQL/flexibleServers/src",
        restore_point_in_time="2024-01-01T00:00:00Z",
    )
    assert config.mode == CreateMode.POINT_IN_TIME_RESTORE
    assert config.restore_point_in_time == "2024-01-01T00:00:00Z"


def test_create_mode_geo_restore_valid() -> None:
    config = MysqlCreateMode(
        mode=CreateMode.GEO_RESTORE,
        source_server_id="/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.DBforMySQL/flexibleServers/src",
    )
    assert config.mode == CreateMode.GEO_RESTORE


def test_create_mode_replica_valid() -> None:
    config = MysqlCreateMode(
        mode=CreateMode.REPLICA,
        source_server_id="/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.DBforMySQL/flexibleServers/src",
    )
    assert config.mode == CreateMode.REPLICA


def test_create_mode_forbids_extra() -> None:
    with pytest.raises(ValueError):
        MysqlCreateMode.model_validate({"extra": "nope"})


# --- MysqlDatabaseConfig ---


def test_database_config_defaults() -> None:
    config = MysqlDatabaseConfig(name="mydb")
    assert config.name == "mydb"
    assert config.charset == "utf8mb4"
    assert config.collation == "utf8mb4_unicode_ci"


def test_database_config_custom() -> None:
    config = MysqlDatabaseConfig(name="mydb", charset="latin1", collation="latin1_swedish_ci")
    assert config.charset == "latin1"
    assert config.collation == "latin1_swedish_ci"


def test_database_config_forbids_extra() -> None:
    with pytest.raises(ValueError):
        MysqlDatabaseConfig.model_validate({"name": "db", "extra": "nope"})


# --- MysqlFlexibleServerConfig ---


def test_server_config_defaults() -> None:
    config = MysqlFlexibleServerConfig()
    assert config.server_name is None
    assert config.server_version == "8.4"
    assert config.network is None
    assert config.allowed_public_networks is None
    assert config.allow_azure_services is False
    assert config.databases is None
    assert config.server_params is None
    assert config.log_workspace_id is None


def test_server_config_vnet_and_firewall_mutually_exclusive() -> None:
    from orbitcloud_graviton.az_network.types import PublicIpv4FirewallRule

    with pytest.raises(ValueError, match="mutually exclusive"):
        MysqlFlexibleServerConfig(
            network=MysqlNetworkConfig(
                subnet_id="/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.Network/virtualNetworks/vnet/subnets/default",
                private_dns_zone_id="/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.Network/privateDnsZones/mysql.database.azure.com",
            ),
            allowed_public_networks=[
                PublicIpv4FirewallRule(name="office", cidr="8.8.8.0/24"),  # type: ignore[arg-type]  # NOSONAR
            ],
        )


def test_server_config_vnet_with_empty_firewall_list_allowed() -> None:
    """Empty list for allowed_public_networks should not trigger mutual exclusion."""
    config = MysqlFlexibleServerConfig(
        network=MysqlNetworkConfig(
            subnet_id="/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.Network/virtualNetworks/vnet/subnets/default",
            private_dns_zone_id="/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.Network/privateDnsZones/mysql.database.azure.com",
        ),
        allowed_public_networks=[],
    )
    assert config.network is not None
    assert config.allowed_public_networks == []


def test_server_config_vnet_and_azure_services_mutually_exclusive() -> None:
    with pytest.raises(ValueError, match="mutually exclusive"):
        MysqlFlexibleServerConfig(
            network=MysqlNetworkConfig(
                subnet_id="/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.Network/virtualNetworks/vnet/subnets/default",
                private_dns_zone_id="/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.Network/privateDnsZones/mysql.database.azure.com",
            ),
            allow_azure_services=True,
        )


def test_server_config_with_network() -> None:
    config = MysqlFlexibleServerConfig(
        network=MysqlNetworkConfig(
            subnet_id="/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.Network/virtualNetworks/vnet/subnets/default",
            private_dns_zone_id="/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.Network/privateDnsZones/mysql.database.azure.com",
        ),
    )
    assert config.network is not None


def test_server_config_with_firewall_rules() -> None:
    from orbitcloud_graviton.az_network.types import PublicIpv4FirewallRule

    config = MysqlFlexibleServerConfig(
        allowed_public_networks=[
            PublicIpv4FirewallRule(name="office", cidr="8.8.8.0/24"),  # type: ignore[arg-type]  # NOSONAR
        ],
    )
    assert config.allowed_public_networks is not None
    assert len(config.allowed_public_networks) == 1


def test_server_config_forbids_extra() -> None:
    with pytest.raises(ValueError):
        MysqlFlexibleServerConfig.model_validate({"extra": "nope"})

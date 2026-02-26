import pytest
from pulumi_azure_native import dbforpostgresql as postgres

from orbitcloud_graviton.az_postgres.flexibleserver import (
    PostgresCreateMode,
    PostgresStorageConfig,
)


# PostgresCreateMode tests
def test_postgres_create_mode_default() -> None:
    mode = PostgresCreateMode.model_validate({})
    assert mode.mode is None
    assert mode.source_server_id is None


def test_postgres_create_mode_point_in_time_restore_requires_source() -> None:
    with pytest.raises(ValueError, match="source_server_id is required when mode is"):
        PostgresCreateMode.model_validate({"mode": postgres.CreateMode.POINT_IN_TIME_RESTORE})


def test_postgres_create_mode_geo_restore_requires_source() -> None:
    with pytest.raises(ValueError, match="source_server_id is required when mode is"):
        PostgresCreateMode.model_validate({"mode": postgres.CreateMode.GEO_RESTORE})


def test_postgres_create_mode_replica_requires_source() -> None:
    with pytest.raises(ValueError, match="source_server_id is required when mode is"):
        PostgresCreateMode.model_validate({"mode": postgres.CreateMode.REPLICA})


def test_postgres_create_mode_valid_point_in_time_restore() -> None:
    mode = PostgresCreateMode.model_validate(
        {
            "mode": postgres.CreateMode.POINT_IN_TIME_RESTORE,
            "source_server_id": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/test/providers/Microsoft.DBforPostgreSQL/flexibleServers/source",
        }
    )
    assert mode.mode == postgres.CreateMode.POINT_IN_TIME_RESTORE
    assert mode.source_server_id is not None


def test_postgres_create_mode_valid_geo_restore() -> None:
    mode = PostgresCreateMode.model_validate(
        {
            "mode": postgres.CreateMode.GEO_RESTORE,
            "source_server_id": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/test/providers/Microsoft.DBforPostgreSQL/flexibleServers/source",
        }
    )
    assert mode.mode == postgres.CreateMode.GEO_RESTORE


def test_postgres_create_mode_valid_replica() -> None:
    mode = PostgresCreateMode.model_validate(
        {
            "mode": postgres.CreateMode.REPLICA,
            "source_server_id": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/test/providers/Microsoft.DBforPostgreSQL/flexibleServers/source",
        }
    )
    assert mode.mode == postgres.CreateMode.REPLICA


# PostgresStorageConfig tests
def test_postgres_storage_config_default() -> None:
    config = PostgresStorageConfig.model_validate({})
    assert config.auto_growth == postgres.StorageAutoGrow.ENABLED
    assert config.storage_size_gb == 32
    assert config.storage_type == postgres.StorageType.PREMIUM_LRS


def test_postgres_storage_config_premium_v2_requires_iops() -> None:
    with pytest.raises(
        ValueError, match="iops and throughput are required when storage_type is PREMIUM_V2_LRS"
    ):
        PostgresStorageConfig.model_validate(
            {
                "storage_type": postgres.StorageType.PREMIUM_V2_LRS,
                "throughput": 200,
            }
        )


def test_postgres_storage_config_premium_v2_requires_throughput() -> None:
    with pytest.raises(
        ValueError, match="iops and throughput are required when storage_type is PREMIUM_V2_LRS"
    ):
        PostgresStorageConfig.model_validate(
            {
                "storage_type": postgres.StorageType.PREMIUM_V2_LRS,
                "iops": 3000,
            }
        )


def test_postgres_storage_config_premium_v2_requires_both() -> None:
    with pytest.raises(
        ValueError, match="iops and throughput are required when storage_type is PREMIUM_V2_LRS"
    ):
        PostgresStorageConfig.model_validate(
            {
                "storage_type": postgres.StorageType.PREMIUM_V2_LRS,
            }
        )


def test_postgres_storage_config_premium_v2_valid() -> None:
    config = PostgresStorageConfig.model_validate(
        {
            "storage_type": postgres.StorageType.PREMIUM_V2_LRS,
            "iops": 3000,
            "throughput": 200,
        }
    )
    assert config.storage_type == postgres.StorageType.PREMIUM_V2_LRS
    assert config.iops == 3000
    assert config.throughput == 200


def test_postgres_storage_config_premium_lrs_no_requirements() -> None:
    config = PostgresStorageConfig.model_validate(
        {
            "storage_type": postgres.StorageType.PREMIUM_LRS,
            "storage_size_gb": 128,
        }
    )
    assert config.storage_type == postgres.StorageType.PREMIUM_LRS
    assert config.storage_size_gb == 128


def test_postgres_storage_config_throughput_min_validation() -> None:
    with pytest.raises(ValueError):
        PostgresStorageConfig.model_validate(
            {
                "storage_type": postgres.StorageType.PREMIUM_V2_LRS,
                "iops": 3000,
                "throughput": 100,  # Below minimum of 125
            }
        )


def test_postgres_storage_config_throughput_max_validation() -> None:
    with pytest.raises(ValueError):
        PostgresStorageConfig.model_validate(
            {
                "storage_type": postgres.StorageType.PREMIUM_V2_LRS,
                "iops": 3000,
                "throughput": 1000,  # Above maximum of 750
            }
        )


def test_postgres_storage_config_storage_size_min_validation() -> None:
    with pytest.raises(ValueError):
        PostgresStorageConfig.model_validate(
            {
                "storage_size_gb": 16,  # Below minimum of 32
            }
        )


def test_postgres_storage_config_storage_size_max_validation() -> None:
    with pytest.raises(ValueError):
        PostgresStorageConfig.model_validate(
            {
                "storage_size_gb": 100000,  # Above maximum of 65536
            }
        )

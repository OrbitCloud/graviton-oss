import importlib.util
import pathlib
import sys

import pytest

# ---------------------------------------------------------------------------
# Load database.py directly. Importing via the package would run az_sql/__init__,
# which pulls in server.py -> az_iam, whose _roles module calls
# asyncio.get_running_loop() at import time and fails during collection. Same
# direct-load pattern used by the az_app http_route tests.
# ---------------------------------------------------------------------------
_db_path = (
    pathlib.Path(__file__).resolve().parents[4]
    / "components"
    / "orbitcloud_graviton"
    / "az_sql"
    / "database.py"
)
_spec = importlib.util.spec_from_file_location(
    "orbitcloud_graviton.az_sql._database_under_test", _db_path
)
assert _spec is not None and _spec.loader is not None
_database = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _database
_spec.loader.exec_module(_database)

SqlElasticPoolSku = _database.SqlElasticPoolSku


def test_name_is_required() -> None:
    with pytest.raises(ValueError):
        SqlElasticPoolSku.model_validate({})


def test_extra_fields_forbidden() -> None:
    with pytest.raises(ValueError):
        SqlElasticPoolSku.model_validate({"name": "GP_Gen5", "unknown": 1})


def test_optional_fields_default_to_none() -> None:
    sku = SqlElasticPoolSku.model_validate({"name": "StandardPool"})
    assert sku.tier is None
    assert sku.capacity is None
    assert sku.family is None
    assert sku.size is None


def test_to_sku_args_maps_all_fields() -> None:
    """The vCore-based fields (capacity, family, size) that the elastic pool
    needs — and that the old SqlDatabaseSku dropped — round-trip into SkuArgs."""
    sku = SqlElasticPoolSku.model_validate(
        {
            "name": "GP_Gen5_4",
            "tier": "GeneralPurpose",
            "capacity": 4,
            "family": "Gen5",
            "size": "4",
        }
    )
    args = sku.to_sku_args()
    assert args.name == "GP_Gen5_4"
    assert args.tier == "GeneralPurpose"
    assert args.capacity == 4
    assert args.family == "Gen5"
    assert args.size == "4"


def test_to_sku_args_dtu_pool_leaves_vcore_fields_none() -> None:
    sku = SqlElasticPoolSku.model_validate(
        {"name": "StandardPool", "tier": "Standard", "capacity": 100}
    )
    args = sku.to_sku_args()
    assert args.name == "StandardPool"
    assert args.tier == "Standard"
    assert args.capacity == 100
    assert args.family is None
    assert args.size is None

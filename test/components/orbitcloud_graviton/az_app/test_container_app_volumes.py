"""Tests for ContainerApp volume mount support.

Covers:
- VolumeMountConfig and VolumeConfig Pydantic model validation
- ContainerConfig.volume_mounts and ContainerAppBaseConfig.volumes fields
- Merge logic in _containers() and _app_template() for secret + Azure File volumes
"""

import importlib.util
import pathlib
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pulumi_azure_native import app
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Module-level stub imports to avoid event-loop errors from transitive deps.
# The az_iam package calls asyncio.get_running_loop() at import time, so we
# stub it *only* if not already loaded (to avoid polluting other test modules).
# ---------------------------------------------------------------------------

_components_dir = pathlib.Path(__file__).resolve().parents[4] / "components"
_az_app_dir = _components_dir / "orbitcloud_graviton" / "az_app"

# Track which modules we stub so we only add what is truly missing.
_stubs_added: list[str] = []


def _stub_module(fqn: str, attrs: dict | None = None) -> None:
    """Register a stub module only if it is not already in sys.modules."""
    if fqn not in sys.modules:
        mod = types.ModuleType(fqn)
        for k, v in (attrs or {}).items():
            setattr(mod, k, v)
        sys.modules[fqn] = mod
        _stubs_added.append(fqn)


# -- az_iam (calls asyncio.get_running_loop at import time) ----------------
_stub_module(
    "orbitcloud_graviton.az_iam",
    {"IamAssignmentConfig": MagicMock, "iam_assignment": MagicMock()},
)

# -- az_acr ----------------------------------------------------------------
_stub_module("orbitcloud_graviton.az_acr", {})
_stub_module(
    "orbitcloud_graviton.az_acr.outputs",
    {"AdminUserEnabledRegistryOutput": MagicMock},
)

# -- az_network (ingress.py imports from it) --------------------------------
_stub_module(
    "orbitcloud_graviton.az_network",
    {"DnsZone": MagicMock, "DnsZoneConfig": MagicMock},
)
_stub_module(
    "orbitcloud_graviton.az_network.dns_zone",
    {"DnsZoneStack": MagicMock},
)
_stub_module(
    "orbitcloud_graviton.az_network.types",
    {
        "CnameRecord": MagicMock,
        "TxtRecord": MagicMock,
        "PrivateIPv4Network": str,
        "PublicIPv4Network": str,
    },
)

# -- az_app package stub ---------------------------------------------------
if "orbitcloud_graviton.az_app" not in sys.modules:
    _pkg = types.ModuleType("orbitcloud_graviton.az_app")
    _pkg.__path__ = [str(_az_app_dir)]  # type: ignore[attr-defined]
    _pkg.__package__ = "orbitcloud_graviton.az_app"
    sys.modules["orbitcloud_graviton.az_app"] = _pkg
    _stubs_added.append("orbitcloud_graviton.az_app")

# ---------------------------------------------------------------------------
# Now load container_app.py via importlib
# ---------------------------------------------------------------------------

_spec = importlib.util.spec_from_file_location(
    "orbitcloud_graviton.az_app.container_app",
    _az_app_dir / "container_app.py",
    submodule_search_locations=[],
)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
sys.modules["orbitcloud_graviton.az_app.container_app"] = _mod
_spec.loader.exec_module(_mod)

VolumeMountConfig = _mod.VolumeMountConfig
VolumeConfig = _mod.VolumeConfig
ContainerConfig = _mod.ContainerConfig
ContainerAppConfig = _mod.ContainerAppConfig
ContainerAppJobConfig = _mod.ContainerAppJobConfig
ContainerAppBaseConfig = _mod.ContainerAppBaseConfig
ContainerApp = _mod.ContainerApp

from orbitcloud_graviton.az_app.secrets import InlineSecret  # noqa: E402
from orbitcloud_graviton.pulumi_lib import AzureStack  # noqa: E402

# Clean up stubs so other test modules can import the real packages.
for _fqn in _stubs_added:
    sys.modules.pop(_fqn, None)


def _make_container_app(
    stack: AzureStack,
    containers: list[ContainerConfig],
    secrets: list | None = None,
    volumes: list[VolumeConfig] | None = None,
    secret_mount_path: Path = Path("/secrets"),
) -> ContainerApp:
    """Build a ContainerApp with a minimal config, bypassing DictRef validation.

    This constructs ContainerAppConfig via model_construct() to skip the
    stack-reference validator on environment_output_ref, then patches just
    enough state on the ContainerApp instance for _containers() and
    _app_template() to be callable.
    """
    config = ContainerAppConfig.model_construct(
        environment_output_ref=None,
        workload_profile_name="Consumption",
        containers=containers,
        secrets=secrets,
        volumes=volumes,
        secret_mount_path=secret_mount_path,
        scaling=None,
        ingress=MagicMock(),
        revision_mode=app.ActiveRevisionsMode.SINGLE,
        name=None,
        registry_output_ref=None,
        resiliency=None,
        log_workspace_id=None,
        azure_permissions=None,
        tags=None,
    )

    # Build a partially-initialised ContainerApp without calling __init__
    # (which would try to create real Pulumi resources).
    ca = ContainerApp.__new__(ContainerApp)
    ca.stack = stack
    ca.config = config
    ca.secrets = secrets or []
    ca.registry = None
    ca._ignores = []
    return ca


# ---------------------------------------------------------------------------
# VolumeMountConfig model tests
# ---------------------------------------------------------------------------


class TestVolumeMountConfig:
    def test_minimal(self) -> None:
        vm = VolumeMountConfig(volume_name="data", mount_path="/mnt/data")
        assert vm.volume_name == "data"
        assert vm.mount_path == "/mnt/data"
        assert vm.sub_path is None

    def test_with_sub_path(self) -> None:
        vm = VolumeMountConfig(volume_name="data", mount_path="/mnt/data", sub_path="subdir")
        assert vm.sub_path == "subdir"

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            VolumeMountConfig(volume_name="data", mount_path="/mnt/data", unknown="bad")


# ---------------------------------------------------------------------------
# VolumeConfig model tests
# ---------------------------------------------------------------------------


class TestVolumeConfig:
    def test_minimal(self) -> None:
        v = VolumeConfig(name="data", storage_name="my-storage")
        assert v.name == "data"
        assert v.storage_name == "my-storage"
        assert v.storage_type == app.StorageType.AZURE_FILE
        assert v.mount_options is None

    def test_nfs_storage_type(self) -> None:
        v = VolumeConfig(
            name="data",
            storage_name="my-storage",
            storage_type=app.StorageType.NFS_AZURE_FILE,
        )
        assert v.storage_type == app.StorageType.NFS_AZURE_FILE

    def test_smb_storage_type(self) -> None:
        v = VolumeConfig(
            name="data",
            storage_name="my-storage",
            storage_type=app.StorageType.SMB,
        )
        assert v.storage_type == app.StorageType.SMB

    def test_with_mount_options(self) -> None:
        v = VolumeConfig(
            name="data",
            storage_name="my-storage",
            mount_options="uid=1000,gid=1000",
        )
        assert v.mount_options == "uid=1000,gid=1000"

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            VolumeConfig(name="data", storage_name="my-storage", unknown="bad")


# ---------------------------------------------------------------------------
# ContainerConfig.volume_mounts field tests
# ---------------------------------------------------------------------------


class TestContainerConfigVolumeMounts:
    def test_defaults_to_none(self) -> None:
        c = ContainerConfig(name="app", image="myimage:latest")
        assert c.volume_mounts is None

    def test_with_volume_mounts(self) -> None:
        c = ContainerConfig(
            name="app",
            image="myimage:latest",
            volume_mounts=[
                VolumeMountConfig(volume_name="data", mount_path="/mnt/data"),
            ],
        )
        assert c.volume_mounts is not None
        assert len(c.volume_mounts) == 1
        assert c.volume_mounts[0].volume_name == "data"

    def test_empty_list(self) -> None:
        c = ContainerConfig(name="app", image="myimage:latest", volume_mounts=[])
        assert c.volume_mounts == []


# ---------------------------------------------------------------------------
# ContainerAppBaseConfig.volumes field tests
# ---------------------------------------------------------------------------

_ENV_REF: dict = {
    "id": {
        "subscription_id": "00000000-0000-0000-0000-000000000000",
        "resource_group_name": "rg",
        "resource_name": "cae",
    },
}


class TestContainerAppBaseConfigVolumes:
    def test_defaults_to_none(self) -> None:
        """volumes defaults to None when not provided."""
        c = ContainerAppBaseConfig.model_construct(
            environment_output_ref=_ENV_REF,
            workload_profile_name="Consumption",
            containers=[ContainerConfig(name="app", image="myimage:latest")],
        )
        assert c.volumes is None

    def test_with_volumes(self) -> None:
        """volumes field accepts a list of VolumeConfig."""
        c = ContainerAppBaseConfig.model_construct(
            environment_output_ref=_ENV_REF,
            workload_profile_name="Consumption",
            containers=[ContainerConfig(name="app", image="myimage:latest")],
            volumes=[
                VolumeConfig(name="data", storage_name="my-storage"),
            ],
        )
        assert c.volumes is not None
        assert len(c.volumes) == 1


# ---------------------------------------------------------------------------
# Integration: _containers() and _app_template() merge logic
# ---------------------------------------------------------------------------


class TestVolumeMergeInContainers:
    """Test that _containers() merges secret volume mounts with Azure File volume mounts."""

    def test_no_volumes_no_secrets_returns_none_mounts(self, stack: AzureStack) -> None:
        """When no secrets with filenames and no volume_mounts, volume_mounts is None."""
        ca = _make_container_app(
            stack=stack,
            containers=[ContainerConfig(name="app", image="myimage:latest")],
        )
        containers = ca._containers()
        assert containers[0].volume_mounts is None

    def test_azure_file_volume_mounts_only(self, stack: AzureStack) -> None:
        """When container has volume_mounts but no secret files, only Azure File mounts appear."""
        ca = _make_container_app(
            stack=stack,
            containers=[
                ContainerConfig(
                    name="app",
                    image="myimage:latest",
                    volume_mounts=[
                        VolumeMountConfig(volume_name="data", mount_path="/mnt/data"),
                    ],
                ),
            ],
        )
        containers = ca._containers()
        mounts = containers[0].volume_mounts
        assert mounts is not None
        assert len(mounts) == 1
        assert mounts[0].volume_name == "data"
        assert mounts[0].mount_path == "/mnt/data"

    def test_secret_and_azure_file_mounts_coexist(self, stack: AzureStack) -> None:
        """When both secret files and Azure File volume_mounts exist, both appear."""
        ca = _make_container_app(
            stack=stack,
            containers=[
                ContainerConfig(
                    name="app",
                    image="myimage:latest",
                    volume_mounts=[
                        VolumeMountConfig(volume_name="data", mount_path="/mnt/data"),
                    ],
                ),
            ],
            secrets=[
                InlineSecret(
                    key="my-secret",
                    value="secret-value",
                    filename="secret.txt",
                ),
            ],
        )
        containers = ca._containers()
        mounts = containers[0].volume_mounts
        assert mounts is not None
        assert len(mounts) == 2
        # Secret mount comes first
        assert mounts[0].volume_name == "secrets"
        assert mounts[0].mount_path == "/secrets"
        # Azure File mount second
        assert mounts[1].volume_name == "data"
        assert mounts[1].mount_path == "/mnt/data"

    def test_volume_mount_with_sub_path(self, stack: AzureStack) -> None:
        """sub_path is passed through to VolumeMountArgs."""
        ca = _make_container_app(
            stack=stack,
            containers=[
                ContainerConfig(
                    name="app",
                    image="myimage:latest",
                    volume_mounts=[
                        VolumeMountConfig(
                            volume_name="data",
                            mount_path="/mnt/data",
                            sub_path="subdir",
                        ),
                    ],
                ),
            ],
        )
        containers = ca._containers()
        mounts = containers[0].volume_mounts
        assert mounts is not None
        assert mounts[0].sub_path == "subdir"

    def test_multiple_containers_independent_mounts(self, stack: AzureStack) -> None:
        """Each container gets its own volume_mounts independently."""
        ca = _make_container_app(
            stack=stack,
            containers=[
                ContainerConfig(
                    name="app",
                    image="myimage:latest",
                    volume_mounts=[
                        VolumeMountConfig(volume_name="data", mount_path="/mnt/data"),
                    ],
                ),
                ContainerConfig(
                    name="sidecar",
                    image="sidecar:latest",
                ),
            ],
        )
        containers = ca._containers()
        assert len(containers) == 2
        assert containers[0].volume_mounts is not None
        assert len(containers[0].volume_mounts) == 1
        assert containers[1].volume_mounts is None


class TestVolumeMergeInAppTemplate:
    """Test that _app_template() merges secret volumes with Azure File volumes."""

    def test_no_volumes_no_secrets_returns_none(self, stack: AzureStack) -> None:
        """When no secret files and no volumes, template volumes is None."""
        ca = _make_container_app(
            stack=stack,
            containers=[ContainerConfig(name="app", image="myimage:latest")],
        )
        template = ca._app_template()
        assert template.volumes is None

    def test_azure_file_volumes_only(self, stack: AzureStack) -> None:
        """When volumes configured but no secret files, only Azure File volumes appear."""
        ca = _make_container_app(
            stack=stack,
            containers=[ContainerConfig(name="app", image="myimage:latest")],
            volumes=[
                VolumeConfig(name="data", storage_name="my-storage"),
            ],
        )
        template = ca._app_template()
        assert template.volumes is not None
        assert len(template.volumes) == 1
        assert template.volumes[0].name == "data"
        assert template.volumes[0].storage_name == "my-storage"
        assert template.volumes[0].storage_type == app.StorageType.AZURE_FILE

    def test_secret_and_azure_file_volumes_coexist(self, stack: AzureStack) -> None:
        """When both secret files and Azure File volumes configured, both appear."""
        ca = _make_container_app(
            stack=stack,
            containers=[ContainerConfig(name="app", image="myimage:latest")],
            secrets=[
                InlineSecret(
                    key="my-secret",
                    value="secret-value",
                    filename="secret.txt",
                ),
            ],
            volumes=[
                VolumeConfig(name="data", storage_name="my-storage"),
            ],
        )
        template = ca._app_template()
        assert template.volumes is not None
        assert len(template.volumes) == 2
        # Secret volume first
        assert template.volumes[0].name == "secrets"
        assert template.volumes[0].storage_type == app.StorageType.SECRET
        # Azure File volume second
        assert template.volumes[1].name == "data"
        assert template.volumes[1].storage_name == "my-storage"
        assert template.volumes[1].storage_type == app.StorageType.AZURE_FILE

    def test_multiple_azure_file_volumes(self, stack: AzureStack) -> None:
        """Multiple Azure File volumes are all included in template."""
        ca = _make_container_app(
            stack=stack,
            containers=[ContainerConfig(name="app", image="myimage:latest")],
            volumes=[
                VolumeConfig(name="private", storage_name="drupal-private"),
                VolumeConfig(
                    name="files",
                    storage_name="drupal-files",
                    storage_type=app.StorageType.NFS_AZURE_FILE,
                ),
            ],
        )
        template = ca._app_template()
        assert template.volumes is not None
        assert len(template.volumes) == 2
        assert template.volumes[0].name == "private"
        assert template.volumes[1].name == "files"
        assert template.volumes[1].storage_type == app.StorageType.NFS_AZURE_FILE

    def test_volume_with_mount_options(self, stack: AzureStack) -> None:
        """mount_options are passed through to VolumeArgs."""
        ca = _make_container_app(
            stack=stack,
            containers=[ContainerConfig(name="app", image="myimage:latest")],
            volumes=[
                VolumeConfig(
                    name="data",
                    storage_name="my-storage",
                    mount_options="uid=1000,gid=1000",
                ),
            ],
        )
        template = ca._app_template()
        assert template.volumes is not None
        assert template.volumes[0].mount_options == "uid=1000,gid=1000"

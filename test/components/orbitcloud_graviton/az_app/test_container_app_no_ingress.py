"""Tests for ContainerApp without ingress.

Azure allows a Container App with no ingress at all (ConfigurationArgs.ingress
is optional): the app has no FQDN and no inbound listener, which is what you
want for a debug/sidecar style container that is only reached via `exec`.

Covers:
- ContainerAppConfig.ingress being optional
- _app_configuration_args() emitting ingress=None
- _outputs() omitting the endpoints export when there is no ingress
"""

import importlib.util
import pathlib
import sys
import types
from unittest.mock import MagicMock

from pulumi_azure_native import app

_components_dir = pathlib.Path(__file__).resolve().parents[4] / "components"
_az_app_dir = _components_dir / "orbitcloud_graviton" / "az_app"

_stubs_added: list[str] = []


def _stub_module(fqn: str, attrs: dict | None = None) -> None:
    if fqn not in sys.modules:
        mod = types.ModuleType(fqn)
        for k, v in (attrs or {}).items():
            setattr(mod, k, v)
        sys.modules[fqn] = mod
        _stubs_added.append(fqn)


_stub_module(
    "orbitcloud_graviton.az_iam",
    {"IamAssignmentConfig": MagicMock, "iam_assignment": MagicMock()},
)
_stub_module("orbitcloud_graviton.az_acr", {})
_stub_module(
    "orbitcloud_graviton.az_acr.outputs",
    {"AdminUserEnabledRegistryOutput": MagicMock},
)
_stub_module(
    "orbitcloud_graviton.az_network",
    {"DnsZone": MagicMock, "DnsZoneConfig": MagicMock},
)
_stub_module("orbitcloud_graviton.az_network.dns_zone", {"DnsZoneStack": MagicMock})
_stub_module(
    "orbitcloud_graviton.az_network.types",
    {
        "CnameRecord": MagicMock,
        "TxtRecord": MagicMock,
        "PrivateIPv4Network": str,
        "PublicIPv4Network": str,
    },
)

if "orbitcloud_graviton.az_app" not in sys.modules:
    _pkg = types.ModuleType("orbitcloud_graviton.az_app")
    _pkg.__path__ = [str(_az_app_dir)]  # type: ignore[attr-defined]
    _pkg.__package__ = "orbitcloud_graviton.az_app"
    sys.modules["orbitcloud_graviton.az_app"] = _pkg
    _stubs_added.append("orbitcloud_graviton.az_app")

_spec = importlib.util.spec_from_file_location(
    "orbitcloud_graviton.az_app.container_app",
    _az_app_dir / "container_app.py",
    submodule_search_locations=[],
)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
sys.modules["orbitcloud_graviton.az_app.container_app"] = _mod
_spec.loader.exec_module(_mod)

ContainerConfig = _mod.ContainerConfig
ContainerAppConfig = _mod.ContainerAppConfig
ContainerApp = _mod.ContainerApp
HttpIngressConfig = _mod.HttpIngressConfig

for _fqn in _stubs_added:
    sys.modules.pop(_fqn, None)


def _config(ingress: object, **overrides: object) -> ContainerAppConfig:
    """Build a ContainerAppConfig bypassing the stack-reference validator."""
    base: dict = {
        "environment_output_ref": None,
        "workload_profile_name": "Consumption",
        "containers": [ContainerConfig(name="netshoot", image="ghcr.io/nicolaka/netshoot")],
        "secrets": None,
        "volumes": None,
        "scaling": None,
        "ingress": ingress,
        "revision_mode": app.ActiveRevisionsMode.SINGLE,
        "name": None,
        "registry_output_ref": None,
        "resiliency": None,
        "azure_permissions": None,
        "tags": None,
    }
    base.update(overrides)
    return ContainerAppConfig.model_construct(**base)


def _container_app(config: ContainerAppConfig) -> ContainerApp:
    ca = ContainerApp.__new__(ContainerApp)
    ca.stack = MagicMock()
    ca.config = config
    ca.secrets = []
    ca.registry = None
    ca._ignores = []
    ca.app = MagicMock(spec=app.ContainerApp)
    return ca


class TestIngressOptional:
    def test_ingress_is_not_required(self) -> None:
        field = ContainerAppConfig.model_fields["ingress"]
        assert not field.is_required()
        assert ContainerAppConfig.model_construct().ingress is None

    def test_ingress_still_accepts_http(self) -> None:
        config = _config(ingress=HttpIngressConfig(protocol="http", target_port=8080))
        assert config.ingress is not None
        assert config.ingress.target_port == 8080


class TestConfigurationArgs:
    def test_no_ingress_emits_none(self) -> None:
        args = _container_app(_config(ingress=None))._app_configuration_args()
        assert args.ingress is None

    def test_ingress_still_emitted(self) -> None:
        config = _config(ingress=HttpIngressConfig(protocol="http", target_port=8080))
        args = _container_app(config)._app_configuration_args()
        assert args.ingress is not None


class TestOutputs:
    def test_endpoints_omitted_without_ingress(self) -> None:
        ca = _container_app(_config(ingress=None))
        ca.register_outputs = MagicMock()
        ca._outputs()

        exports = ca.stack.export.call_args.kwargs["exports"]
        assert "endpoints" not in exports["app"]
        assert set(exports["app"]) == {"id", "name"}

"""
YAML-based resource metadata loader.

Reads all YAML service files from the services/ directory at import time,
builds the hierarchical _azure_resource_meta structure and the flat
RESOURCE_PREFIXES lookup, and caches the results.

Data is loaded once at module import time -- no per-call file I/O.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

_SERVICES_DIR = Path(__file__).parent / "services"

# ---------------------------------------------------------------------------
# Pydantic validation models
# ---------------------------------------------------------------------------


class NamingRuleSchema(BaseModel):
    """Validates the naming block inside a resource entry."""

    prefix: str
    alphanumeric: bool = False
    lowercase: bool = False
    max_length: int | None = None

    model_config = ConfigDict(extra="forbid")


class ResourceSchema(BaseModel):
    """Validates a single resource entry in a service YAML file."""

    naming: NamingRuleSchema
    namespace: str | None = None
    resource_type: str | None = None
    sub_resource_name: str | None = None
    public_dns_zone: str | None = None
    private_dns_zone: str | None = None

    model_config = ConfigDict(extra="forbid")


class ServiceFileSchema(BaseModel):
    """Validates the top-level structure of a service YAML file."""

    azure_namespace: str | None = None
    resources: dict[str, ResourceSchema]

    model_config = ConfigDict(extra="forbid")


class RegionSchema(BaseModel):
    """Validates a single region entry."""

    name: str
    abbr: str

    model_config = ConfigDict(extra="forbid")


class RegionsFileSchema(BaseModel):
    """Validates the top-level structure of regions.yaml."""

    regions: dict[str, RegionSchema]

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# PascalCase to snake_case conversion
# ---------------------------------------------------------------------------


def _pascal_to_snake(name: str) -> str:
    """Convert PascalCase class name to snake_case module path segment.

    Examples:
        ResourceGroup -> resource_group
        P2sVpnGateway -> p2s_vpn_gateway
        StorageAccount -> storage_account
    """
    # Insert underscore at each word boundary: before an uppercase letter that follows
    # a lowercase/digit, or between an uppercase letter and an uppercase-then-lowercase pair.
    # Uses a single lookahead/lookbehind pattern to avoid backtracking.
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", name)
    return s.lower()


# ---------------------------------------------------------------------------
# Explicit v1 module path overrides
# ---------------------------------------------------------------------------

# Maps (yaml_filename_stem, ClassName) -> full v1 module path.
# Used when the auto-derived path from _pascal_to_snake doesn't match the
# actual Pulumi SDK module path used by RESOURCE_PREFIXES.
_V1_MODULE_PATH_OVERRIDES: dict[tuple[str, str], str] = {
    # pulumi_random uses "pulumi_random" not "pulumi_azure_native"
    ("random", "RandomPassword"): "pulumi_random.random_password",
    # Pulumi SDK module is "app_service" but class is "WebApp"
    ("web", "WebApp"): "pulumi_azure_native.web.app_service",
    # EventHub class in Pulumi SDK uses module "event_hub" not "eventhub"
    ("eventhub", "EventHub"): "pulumi_azure_native.eventhub.event_hub",
}

# Some YAML class names should be EXCLUDED from v1 RESOURCE_PREFIXES because
# they are aliases that only exist for v2 lookups (where class name matters).
# For example, insights.yaml has "Diagnosticsetting" for v2 compat but the
# actual v1 key is "monitor.diagnostic_setting" from monitor.yaml.
_V1_EXCLUDE_ENTRIES: set[tuple[str, str]] = {
    # insights.yaml entries are for v2 only -- v1 uses applicationinsights and monitor modules
    ("insights", "Component"),
    ("insights", "Diagnosticsetting"),
    ("insights", "DiagnosticSetting"),
    # eventhub.yaml "Eventhub" is a v2 alias -- v1 uses "EventHub" -> event_hub
    ("eventhub", "Eventhub"),
}


# ---------------------------------------------------------------------------
# The set of YAML filenames that contribute to the v2 hierarchical structure
# ---------------------------------------------------------------------------

_V2_SERVICE_FILES = {
    "app",
    "appconfiguration",
    "authorization",
    "cognitiveservices",
    "containerregistry",
    "eventgrid",
    "eventhub",
    "insights",
    "keyvault",
    "network",
    "operationalinsights",
    "providerhub",
    "resources",
    "search",
    "servicebus",
    "sql",
    "storage",
    "web",
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _load_service_file(path: Path) -> ServiceFileSchema:
    """Load and validate a single service YAML file."""
    with open(path) as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raise ValueError(f"Empty YAML file: {path}")

    try:
        return ServiceFileSchema.model_validate(raw)
    except ValidationError as e:
        raise ValueError(f"Invalid YAML schema in {path.name}: {e}") from e


def _load_regions_file(path: Path) -> dict[str, dict[str, str]]:
    """Load and validate regions.yaml, returning the legacy dict format."""
    with open(path) as f:
        raw = yaml.safe_load(f)

    validated = RegionsFileSchema.model_validate(raw)
    return {
        key: {"name": region.name, "abbr": region.abbr} for key, region in validated.regions.items()
    }


def _resource_to_dict(resource: ResourceSchema) -> dict[str, Any]:
    """Convert a validated ResourceSchema back to the legacy dict format
    used by _azure_resource_meta."""
    result: dict[str, Any] = {}

    # Build naming dict, only including non-default values
    naming: dict[str, Any] = {"prefix": resource.naming.prefix}
    if resource.naming.alphanumeric:
        naming["alphanumeric"] = True
    if resource.naming.lowercase:
        naming["lowercase"] = True
    if resource.naming.max_length is not None:
        naming["max_length"] = resource.naming.max_length

    result["naming"] = naming

    if resource.namespace is not None:
        result["namespace"] = resource.namespace
    if resource.resource_type is not None:
        result["resource_type"] = resource.resource_type
    if resource.sub_resource_name is not None:
        result["sub_resource_name"] = resource.sub_resource_name
    if resource.public_dns_zone is not None:
        result["public_dns_zone"] = resource.public_dns_zone
    if resource.private_dns_zone is not None:
        result["private_dns_zone"] = resource.private_dns_zone

    return result


def _naming_to_v1_dict(naming: NamingRuleSchema) -> dict[str, Any]:
    """Convert a NamingRuleSchema to the v1 RESOURCE_PREFIXES dict format."""
    result: dict[str, Any] = {"prefix": naming.prefix}
    if naming.alphanumeric:
        result["alphanumeric"] = True
    if naming.lowercase:
        result["lowercase"] = True
    if naming.max_length is not None:
        result["max_length"] = naming.max_length
    return result


# ---------------------------------------------------------------------------
# Core loader
# ---------------------------------------------------------------------------


def _load_all() -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, str]]]:
    """Load all YAML files and build both data structures.

    Returns:
        (azure_resource_meta, resource_prefixes, azure_regions)
    """
    azure_resource_meta: dict[str, Any] = {"pulumi_azure_native": {}}
    resource_prefixes: dict[str, Any] = {}

    regions_path = _SERVICES_DIR / "regions.yaml"
    if not regions_path.exists():
        raise FileNotFoundError(f"Missing regions file: {regions_path}")
    azure_regions = _load_regions_file(regions_path)

    # Load all service YAML files
    for yaml_path in sorted(_SERVICES_DIR.glob("*.yaml")):
        if yaml_path.name == "regions.yaml":
            continue

        stem = yaml_path.stem  # e.g., "keyvault", "dns", "random"
        service = _load_service_file(yaml_path)

        # Build v2 hierarchical structure only for the original v2 namespaces
        if stem in _V2_SERVICE_FILES:
            ns_data: dict[str, Any] = {}
            if service.azure_namespace is not None:
                ns_data["namespace"] = service.azure_namespace
            ns_data["resources"] = {}
            for class_name, resource in service.resources.items():
                ns_data["resources"][class_name] = _resource_to_dict(resource)
            azure_resource_meta["pulumi_azure_native"][stem] = ns_data

        # Build v1 flat lookup for ALL files
        for class_name, resource in service.resources.items():
            # Skip entries that are v2-only aliases
            if (stem, class_name) in _V1_EXCLUDE_ENTRIES:
                continue

            override_key = (stem, class_name)
            if override_key in _V1_MODULE_PATH_OVERRIDES:
                module_path = _V1_MODULE_PATH_OVERRIDES[override_key]
            else:
                snake_name = _pascal_to_snake(class_name)
                module_path = f"pulumi_azure_native.{stem}.{snake_name}"

            resource_prefixes[module_path] = _naming_to_v1_dict(resource.naming)

    return azure_resource_meta, resource_prefixes, azure_regions


# ---------------------------------------------------------------------------
# Module-level cached data (loaded once at import time)
# ---------------------------------------------------------------------------

_azure_resource_meta, RESOURCE_PREFIXES, _azure_regions = _load_all()

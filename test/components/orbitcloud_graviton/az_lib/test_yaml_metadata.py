"""
Tests for YAML-based resource metadata loading and validation.

Verifies that all YAML files load correctly, every resource has a naming.prefix,
and the loader produces valid data structures.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from orbitcloud_graviton.az_lib.metadata.loader import (
    RESOURCE_PREFIXES,
    ServiceFileSchema,
    _azure_regions,
    _azure_resource_meta,
    _load_service_file,
)

_SERVICES_DIR = Path(__file__).parents[4] / (
    "components/orbitcloud_graviton/az_lib/metadata/services"
)


class TestYamlFilesLoadSuccessfully:
    """All YAML files in services/ must load and validate without errors."""

    @pytest.fixture
    def yaml_files(self) -> list[Path]:
        return sorted(_SERVICES_DIR.glob("*.yaml"))

    def test_services_directory_exists(self) -> None:
        assert _SERVICES_DIR.is_dir(), f"Services directory not found: {_SERVICES_DIR}"

    def test_at_least_one_yaml_file_exists(self, yaml_files: list[Path]) -> None:
        assert len(yaml_files) > 0, "No YAML files found in services/"

    def test_regions_yaml_exists(self) -> None:
        assert (_SERVICES_DIR / "regions.yaml").exists(), "regions.yaml not found"

    @pytest.mark.parametrize(
        "yaml_file",
        sorted(_SERVICES_DIR.glob("*.yaml")),
        ids=lambda p: p.stem,
    )
    def test_yaml_file_is_valid_yaml(self, yaml_file: Path) -> None:
        """Each YAML file must be parseable."""
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
        assert data is not None, f"{yaml_file.name} is empty"
        assert isinstance(data, dict), f"{yaml_file.name} root is not a dict"

    @pytest.mark.parametrize(
        "yaml_file",
        [p for p in sorted(_SERVICES_DIR.glob("*.yaml")) if p.name != "regions.yaml"],
        ids=lambda p: p.stem,
    )
    def test_service_yaml_validates_against_schema(self, yaml_file: Path) -> None:
        """Each service YAML file must validate against the Pydantic schema."""
        service = _load_service_file(yaml_file)
        assert isinstance(service, ServiceFileSchema)
        assert len(service.resources) > 0, f"{yaml_file.name} has no resources"


class TestEveryResourceHasNamingPrefix:
    """Every resource in every YAML file must have a naming.prefix field."""

    def test_all_v2_resources_have_naming_prefix(self) -> None:
        """Every resource in the v2 hierarchical structure must have naming.prefix."""
        for ns_key, ns_data in _azure_resource_meta["pulumi_azure_native"].items():
            for class_name, resource_data in ns_data["resources"].items():
                assert "naming" in resource_data, f"{ns_key}.{class_name} is missing 'naming' key"
                assert "prefix" in resource_data["naming"], (
                    f"{ns_key}.{class_name} is missing 'naming.prefix'"
                )
                assert isinstance(resource_data["naming"]["prefix"], str), (
                    f"{ns_key}.{class_name} naming.prefix is not a string"
                )
                assert len(resource_data["naming"]["prefix"]) > 0, (
                    f"{ns_key}.{class_name} naming.prefix is empty"
                )

    def test_all_v1_resources_have_prefix(self) -> None:
        """Every entry in RESOURCE_PREFIXES must have a 'prefix' key."""
        for module_path, opts in RESOURCE_PREFIXES.items():
            assert "prefix" in opts, f"{module_path} is missing 'prefix' key"
            assert isinstance(opts["prefix"], str), f"{module_path} prefix is not a string"
            assert len(opts["prefix"]) > 0, f"{module_path} prefix is empty"


class TestRegionsYamlLoadsCorrectly:
    """regions.yaml must load and produce valid region data."""

    def test_regions_not_empty(self) -> None:
        assert len(_azure_regions) > 0, "No regions loaded"

    def test_all_regions_have_name_and_abbr(self) -> None:
        for region_key, region_data in _azure_regions.items():
            assert "name" in region_data, f"Region {region_key} missing 'name'"
            assert "abbr" in region_data, f"Region {region_key} missing 'abbr'"
            assert isinstance(region_data["name"], str)
            assert isinstance(region_data["abbr"], str)
            assert len(region_data["abbr"]) > 0, f"Region {region_key} has empty abbr"


class TestLoaderDataIntegrity:
    """Verify the loader produces consistent, complete data."""

    def test_v2_structure_has_pulumi_azure_native(self) -> None:
        assert "pulumi_azure_native" in _azure_resource_meta

    def test_v2_namespaces_are_non_empty(self) -> None:
        for ns_key, ns_data in _azure_resource_meta["pulumi_azure_native"].items():
            assert "resources" in ns_data, f"Namespace {ns_key} missing 'resources'"
            assert len(ns_data["resources"]) > 0, f"Namespace {ns_key} has no resources"

    def test_resource_prefixes_is_non_empty(self) -> None:
        assert len(RESOURCE_PREFIXES) > 0

    def test_no_duplicate_v1_prefixes_accidentally_overwritten(self) -> None:
        """Verify the total count of v1 entries matches expectations."""
        # We know the exact count from the original _prefixes.py (67 entries)
        # plus any intentional additions
        assert len(RESOURCE_PREFIXES) >= 67, (
            f"Expected at least 67 v1 entries, got {len(RESOURCE_PREFIXES)}"
        )

    def test_containerregistry_namespace_typo_is_fixed(self) -> None:
        """The Micrsoft typo must be fixed to Microsoft."""
        cr_ns = _azure_resource_meta["pulumi_azure_native"]["containerregistry"]
        assert cr_ns["namespace"] == "Microsoft.ContainerRegistry", (
            f"Expected 'Microsoft.ContainerRegistry', got {cr_ns['namespace']!r}"
        )

    def test_blob_container_prefix_is_stctr(self) -> None:
        """BlobContainer prefix must be 'stctr' (the v1/production value)."""
        v1 = RESOURCE_PREFIXES["pulumi_azure_native.storage.blob_container"]["prefix"]
        v2 = _azure_resource_meta["pulumi_azure_native"]["storage"]["resources"]["BlobContainer"][
            "naming"
        ]["prefix"]
        assert v1 == "stctr"
        assert v2 == "stctr"

    def test_app_service_plan_has_naming_wrapper(self) -> None:
        """AppServicePlan must have the proper naming wrapper."""
        asp = _azure_resource_meta["pulumi_azure_native"]["web"]["resources"]["AppServicePlan"]
        assert "naming" in asp, "AppServicePlan missing 'naming' wrapper"
        assert asp["naming"]["prefix"] == "asp"

    def test_record_set_prefix_has_no_trailing_comma(self) -> None:
        """RecordSet prefix 'dnsr,' typo must be fixed to 'dnsr'."""
        v1 = RESOURCE_PREFIXES["pulumi_azure_native.dns.record_set"]["prefix"]
        assert v1 == "dnsr", f"Expected 'dnsr', got {v1!r}"


class TestInvalidYamlHandling:
    """Verify error handling for malformed YAML data."""

    def test_empty_yaml_raises(self, tmp_path: Path) -> None:
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("")
        with pytest.raises(ValueError, match="Empty YAML file"):
            _load_service_file(empty_file)

    def test_missing_naming_prefix_raises(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("resources:\n  Foo:\n    naming:\n      alphanumeric: true\n")
        with pytest.raises(ValueError, match="Invalid YAML schema"):
            _load_service_file(bad_file)

    def test_extra_fields_raises(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "extra.yaml"
        bad_file.write_text(
            "resources:\n  Foo:\n    naming:\n      prefix: test\n    unknown_field: bad\n"
        )
        with pytest.raises(ValueError, match="Invalid YAML schema"):
            _load_service_file(bad_file)

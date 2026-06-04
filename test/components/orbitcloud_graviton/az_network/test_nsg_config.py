import pytest

from orbitcloud_graviton.az_network import helpers
from orbitcloud_graviton.az_network.helpers import DEFAULT_SERVICE_TAGS, is_service_tag
from orbitcloud_graviton.az_network.nsg import NsgRuleConfig


def _no_api_call(*args, **kwargs):  # noqa: ARG001
    raise AssertionError("fetch_service_tags should not be called for default service tags")


@pytest.mark.parametrize("tag", sorted(DEFAULT_SERVICE_TAGS))
def test_default_service_tags_are_valid_without_api(tag: str, monkeypatch) -> None:
    """Default/system tags (VirtualNetwork, AzureLoadBalancer, Internet) are not
    returned by the serviceTags.list API, so they must validate without an API call."""
    monkeypatch.setattr(helpers, "fetch_service_tags", _no_api_call)
    assert is_service_tag(tag) == tag


def test_nsg_rule_accepts_virtualnetwork_service_tag(monkeypatch) -> None:
    """An NSG rule using the VirtualNetwork service tag validates offline."""
    monkeypatch.setattr(helpers, "fetch_service_tags", _no_api_call)
    rule = NsgRuleConfig.model_validate(
        {
            "name": "allow-vnet",
            "source_addresses": "VirtualNetwork",
            "destination_addresses": "VirtualNetwork",
        }
    )
    assert rule.source_addresses == "VirtualNetwork"


def test_non_default_service_tag_falls_through_to_api(monkeypatch) -> None:
    """A non-default tag is validated against the API-provided list."""
    monkeypatch.setattr(helpers, "fetch_service_tags", lambda location: ["AzureCloud"])
    assert is_service_tag("AzureCloud") == "AzureCloud"


def test_invalid_service_tag_raises(monkeypatch) -> None:
    monkeypatch.setattr(helpers, "fetch_service_tags", lambda location: ["AzureCloud"])
    with pytest.raises(ValueError, match="is not a valid service tag"):
        is_service_tag("NotARealTag")

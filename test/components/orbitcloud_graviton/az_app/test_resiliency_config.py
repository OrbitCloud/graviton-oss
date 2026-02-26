import importlib.util
import sys
import types

import pytest

# Workaround: Import resiliency module directly without triggering az_app/__init__.py
# which has an import chain that fails outside of Pulumi runtime (asyncio loop issue)
if "orbitcloud_graviton.az_app" not in sys.modules:
    sys.modules["orbitcloud_graviton.az_app"] = types.ModuleType("orbitcloud_graviton.az_app")

_spec = importlib.util.spec_from_file_location(
    "orbitcloud_graviton.az_app.resiliency",
    "components/orbitcloud_graviton/az_app/resiliency.py",
)
_resiliency = importlib.util.module_from_spec(_spec)
sys.modules["orbitcloud_graviton.az_app.resiliency"] = _resiliency
_spec.loader.exec_module(_resiliency)

ResiliencyHttpHeaders = _resiliency.ResiliencyHttpHeaders
ResiliencyHttpRetry = _resiliency.ResiliencyHttpRetry


# ResiliencyHttpHeaders tests
def test_resiliency_http_headers_exact_match() -> None:
    headers = ResiliencyHttpHeaders.model_validate(
        {"name": "Content-Type", "exact_match": "application/json"}
    )
    assert headers.name == "Content-Type"
    assert headers.exact_match == "application/json"
    assert headers.prefix_match is None
    assert headers.suffix_match is None


def test_resiliency_http_headers_prefix_match() -> None:
    headers = ResiliencyHttpHeaders.model_validate({"name": "X-Custom", "prefix_match": "prefix-"})
    assert headers.prefix_match == "prefix-"
    assert headers.exact_match is None


def test_resiliency_http_headers_suffix_match() -> None:
    headers = ResiliencyHttpHeaders.model_validate({"name": "X-Custom", "suffix_match": "-suffix"})
    assert headers.suffix_match == "-suffix"
    assert headers.exact_match is None


def test_resiliency_http_headers_no_match_method() -> None:
    with pytest.raises(
        ValueError, match="Exactly one of 'exact_match', 'prefix_match', 'suffix_match' must be set"
    ):
        ResiliencyHttpHeaders.model_validate({"name": "Content-Type"})


def test_resiliency_http_headers_multiple_match_methods() -> None:
    with pytest.raises(
        ValueError, match="Exactly one of 'exact_match', 'prefix_match', 'suffix_match' must be set"
    ):
        ResiliencyHttpHeaders.model_validate(
            {
                "name": "Content-Type",
                "exact_match": "application/json",
                "prefix_match": "application/",
            }
        )


def test_resiliency_http_headers_all_match_methods() -> None:
    with pytest.raises(
        ValueError, match="Exactly one of 'exact_match', 'prefix_match', 'suffix_match' must be set"
    ):
        ResiliencyHttpHeaders.model_validate(
            {
                "name": "Content-Type",
                "exact_match": "application/json",
                "prefix_match": "application/",
                "suffix_match": "/json",
            }
        )


# ResiliencyHttpRetry tests
def test_resiliency_http_retry_basic() -> None:
    retry = ResiliencyHttpRetry.model_validate(
        {
            "error_types": ["5xx"],
            "max_retries": 3,
            "initial_delay_ms": 100,
            "max_interval_ms": 1000,
        }
    )
    assert retry.error_types == ["5xx"]
    assert retry.max_retries == 3
    assert retry.initial_delay_ms == 100
    assert retry.max_interval_ms == 1000


def test_resiliency_http_retry_multiple_error_types() -> None:
    retry = ResiliencyHttpRetry.model_validate(
        {
            "error_types": ["5xx", "connect-failure", "reset"],
            "max_retries": 5,
            "initial_delay_ms": 200,
            "max_interval_ms": 2000,
        }
    )
    assert len(retry.error_types) == 3
    assert "5xx" in retry.error_types
    assert "connect-failure" in retry.error_types


def test_resiliency_http_retry_retriable_headers_requires_headers() -> None:
    with pytest.raises(
        ValueError,
        match="If 'retriable-headers' is in 'error_types', 'headers' must be set and vice versa",
    ):
        ResiliencyHttpRetry.model_validate(
            {
                "error_types": ["retriable-headers"],
                "max_retries": 3,
                "initial_delay_ms": 100,
                "max_interval_ms": 1000,
            }
        )


def test_resiliency_http_retry_headers_require_retriable_headers() -> None:
    with pytest.raises(
        ValueError,
        match="If 'retriable-headers' is in 'error_types', 'headers' must be set and vice versa",
    ):
        ResiliencyHttpRetry.model_validate(
            {
                "error_types": ["5xx"],
                "max_retries": 3,
                "initial_delay_ms": 100,
                "max_interval_ms": 1000,
                "headers": [{"name": "X-Retry", "exact_match": "true"}],
            }
        )


def test_resiliency_http_retry_retriable_headers_with_headers_valid() -> None:
    retry = ResiliencyHttpRetry.model_validate(
        {
            "error_types": ["retriable-headers"],
            "max_retries": 3,
            "initial_delay_ms": 100,
            "max_interval_ms": 1000,
            "headers": [{"name": "X-Retry", "exact_match": "true"}],
        }
    )
    assert "retriable-headers" in retry.error_types
    assert retry.headers is not None
    assert len(retry.headers) == 1


def test_resiliency_http_retry_with_status_codes() -> None:
    retry = ResiliencyHttpRetry.model_validate(
        {
            "error_types": ["retriable-status-codes"],
            "max_retries": 3,
            "initial_delay_ms": 100,
            "max_interval_ms": 1000,
            "http_status_codes": [408, 429, 503],
        }
    )
    assert retry.http_status_codes == [408, 429, 503]


def test_resiliency_http_retry_max_retries_validation() -> None:
    with pytest.raises(ValueError):
        ResiliencyHttpRetry.model_validate(
            {
                "error_types": ["5xx"],
                "max_retries": 0,  # Must be > 0
                "initial_delay_ms": 100,
                "max_interval_ms": 1000,
            }
        )


def test_resiliency_http_retry_initial_delay_validation() -> None:
    with pytest.raises(ValueError):
        ResiliencyHttpRetry.model_validate(
            {
                "error_types": ["5xx"],
                "max_retries": 3,
                "initial_delay_ms": 0,  # Must be > 0
                "max_interval_ms": 1000,
            }
        )


def test_resiliency_http_retry_max_interval_validation() -> None:
    with pytest.raises(ValueError):
        ResiliencyHttpRetry.model_validate(
            {
                "error_types": ["5xx"],
                "max_retries": 3,
                "initial_delay_ms": 100,
                "max_interval_ms": -1,  # Must be > 0
            }
        )

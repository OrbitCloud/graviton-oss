"""Azure helper functions for OrbitCloud Graviton"""

from .aio import async_output, in_event_loop
from .helpers import fmt_name, location_abbr
from .naming_v1 import get_prefix, resource_namer
from .network import is_public_ip
from .types import AzureIdRef, AzureResourceId

__all__ = [
    "is_public_ip",
    "resource_namer",
    "location_abbr",
    "get_prefix",
    "AzureResourceId",
    "AzureIdRef",
    "fmt_name",
    "async_output",
    "in_event_loop",
]

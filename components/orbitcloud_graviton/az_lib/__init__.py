""" Azure helper functions for OrbitCloud Graviton """

from .naming import location_abbr, resource_namer, resource_opts
from .network import is_public_ip
from .resources import get_resource_name_from_id
from .types import AzureIdRef, AzureResourceId

__all__ = [
    "is_public_ip",
    "resource_namer",
    "location_abbr",
    "resource_opts",
    "get_resource_name_from_id",
    "AzureResourceId",
    "AzureIdRef",
]

""" Azure helper functions for OrbitCloud Graviton """

from .config import Confy, StackConfig
from .naming import location_abbr, resource_namer, resource_opts

__all__ = [
    "resource_namer",
    "location_abbr",
    "resource_opts",
    "StackConfig",
    "Confy",
]

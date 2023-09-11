""" Azure helper functions for OrbitCloud Graviton """

from .naming import (
    resource_namer,
    location_abbr,
    resource_opts,
)

from .config import BaseConfig, StackConfig

__all__ = [
    "resource_namer",
    "location_abbr",
    "resource_opts",
    "BaseConfig",
    "StackConfig",
]

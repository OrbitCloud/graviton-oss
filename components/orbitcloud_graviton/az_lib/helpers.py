import re
from collections.abc import Sequence
from typing import Literal

import pulumi

from .metadata.azure import _azure_regions


def fmt_name(
    v: str | Sequence,
    sep: str | None = "-",
    case: Literal["lower", "title"] = "lower",
) -> str:
    sep = "" if sep is None else sep

    def _format(_str) -> str:
        # split by space, -, _, ., /, :
        parts: list[str] = re.split(pattern=r"[\s\-\._/:]", string=_str)
        if case == "title":
            return sep.join([part.title() for part in parts])

        return sep.join([part.lower() for part in parts])

    if isinstance(v, Sequence) and not isinstance(v, str):
        return sep.join([_format(part) for part in v])

    if isinstance(v, pulumi.Output):
        return v.apply(lambda v: _format(v))  # type: ignore

    return _format(v)


def location_abbr(location: str) -> str:
    """Return a location abbreviation for a given location"""
    region: dict[str, str] | None = _azure_regions.get(location)

    if not region:
        raise ValueError(f"Region settings have not been defined for: {location}")

    abbr: str | None = region.get("abbr")
    if not abbr:
        raise ValueError(f"Abbreviation has not been defined for: {location}")

    return abbr

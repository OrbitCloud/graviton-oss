# Create an annotated Pydantic type for domain
import re
from typing import Annotated

from pydantic import BeforeValidator


def domain_validator(domain: str) -> str:
    # See pattern https://regexr.com/3gcrp
    if re.fullmatch(
        r"([a-z0-9A-Z]\.)*[a-z0-9-]+\.([a-z0-9]{2,24})+(\.co\.([a-z0-9]{2,24})|\.([a-z0-9]{2,24}))*",
        domain,
    ):
        return domain
    raise ValueError(f"{domain} is not a valid domain name.")


DomainName = Annotated[str, BeforeValidator(domain_validator)]

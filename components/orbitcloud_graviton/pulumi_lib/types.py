# Create an annotated Pydantic type for domain
import re
from typing import Annotated

import pulumi
from pulumi_random import RandomString
from pydantic import AfterValidator, BeforeValidator, EmailStr


def domain_validator(domain: str) -> str:
    # See pattern https://regexr.com/3gcrp
    if re.fullmatch(
        r"([a-z0-9A-Z]\.)*[a-z0-9-]+\.([a-z0-9]{2,24})+(\.co\.([a-z0-9]{2,24})|\.([a-z0-9]{2,24}))*",
        domain,
    ):
        return domain
    raise ValueError(f"{domain} is not a valid domain name.")


DomainName = Annotated[str, BeforeValidator(domain_validator)]


def email_random_plus(email: EmailStr) -> EmailStr | pulumi.Output[EmailStr]:
    if "+" not in email.split("@")[0]:
        random = RandomString(
            resource_name=f"rand-plus-{email}",
            length=5,
            special=False,
        )

        return pulumi.Output.concat(
            email.split("@")[0], "+", random.result, "@", email.split("@")[1]
        )
    return email


RandomPlusEmail = Annotated[EmailStr, AfterValidator(email_random_plus)]

# Create an annotated Pydantic type for domain
import datetime
import re
from typing import Annotated, Any

import pulumi
from pulumi_random import RandomString
from pulumiverse_time import Rotating, RotatingArgs
from pydantic import (
    AfterValidator,
    BeforeValidator,
    EmailStr,
    GetCoreSchemaHandler,
    ValidationInfo,
)
from pydantic_core import core_schema


def domain_validator(domain: str) -> str:
    # See pattern https://regexr.com/3gcrp
    if re.fullmatch(
        r"([a-z0-9A-Z_\-]\.)*[a-z0-9_\-]+\.([a-z0-9_\-]{2,64})+(\.co\.([a-z0-9]{2,24})|\.([a-z0-9]{2,24}))*",
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


def tokenize(value: str, allowed_literals: list | None = None) -> tuple[int, str]:
    """
    Tokenize a text into number and string.
    >>> tokenize("10m")
    ('10', 'm')
    >>> tokenize("1d")
    ('1', 'd')
    """
    token: tuple = re.findall(pattern=r"(\d+)([a-zA-Z]+)", string=value)[0]

    if len(token) != 2 or not token[0].isdigit() or not token[1]:
        raise ValueError(f"Invalid token: {value} expected format: <int><string>, e.g. 10m")

    if allowed_literals and token[1] not in allowed_literals:
        raise ValueError(f"Invalid token: {value} allowed literals: {allowed_literals}")

    return token


def future_datetime(delta: str) -> datetime.timedelta:
    allowed_literals: list[str] = [
        "m",
        "min",
        "minutes",
        "h",
        "hours",
        "d",
        "days",
        "w",
        "weeks",
        "M",
        "months",
        "y",
        "years",
    ]

    digit, literal = tokenize(value=delta, allowed_literals=allowed_literals)

    if literal in ["m", "min", "minutes"]:
        return datetime.timedelta(minutes=int(digit))
    if literal in ["h", "hours"]:
        return datetime.timedelta(hours=int(digit))
    if literal in ["d", "days"]:
        return datetime.timedelta(days=int(digit))
    if literal in ["w", "weeks"]:
        return datetime.timedelta(weeks=int(digit))
    if literal in ["M", "months"]:
        # 30 days in a month
        return datetime.timedelta(days=int(digit) * 30)
    if literal in ["y", "years"]:
        return datetime.timedelta(weeks=int(digit) * 52)

    raise ValueError(f"Invalid token: {delta} allowed literals: {allowed_literals}")


class TimeFromNow(str):
    def __init__(self, after: str) -> None:
        self.delta: datetime.timedelta = future_datetime(delta=after)
        self.seconds: int = self.delta.seconds
        self.minutes: int = self.delta.seconds // 60
        self.hours: int = self.delta.seconds // 3600
        self.days: int = self.delta.days
        self.weeks: int = self.delta.days // 7
        self.months: int = self.delta.days // 30
        self.years: int = self.delta.days // 365

    def __new__(cls, after: str) -> "TimeFromNow":
        return super().__new__(cls, after)

    @property
    def timedelta(self) -> datetime.timedelta:
        return self.delta

    def to_datetime(self) -> datetime.datetime:
        return datetime.datetime.now() + self.delta

    def rotating_rep(self) -> dict[str, Any]:
        for unit in ["years", "months", "days", "hours", "minutes"]:
            value = getattr(self, unit)
            if value:
                return {f"rotation_{unit}": value}
        return {"rotation_seconds": self.seconds}

    def Rotating(
        self,
        resource_name: str,
        triggers: dict[str, str] | None = None,
        opts: pulumi.ResourceOptions | None = None,
    ) -> Rotating:
        return Rotating(
            resource_name=resource_name,
            args=RotatingArgs(
                **self.rotating_rep(),
                triggers=triggers,
            ),
            opts=opts,
        )

    def __repr__(self) -> str:
        return "TimeFromNow"

    @classmethod
    def validate(cls, value: str, info: ValidationInfo):
        return cls(value)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.with_info_after_validator_function(
            function=cls.validate, schema=handler(str), field_name=handler.field_name
        )

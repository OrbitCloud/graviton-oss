from typing import Optional, Sequence, Union

import pulumi
from pulumi_azure_native import provider


def fmt_name(v: Union[str, pulumi.Output[str], Sequence], sep: Optional[str] = "-") -> str:
    def format(v):
        return v.lower().replace(" ", sep).replace("_", sep).replace(".", sep)

    if isinstance(v, Sequence) and not isinstance(v, str):
        return "-".join([format(str(n)) for n in v])
    return format(v)


def get_provider(subscription_id) -> provider.Provider:
    """Returns a provider for a given subscription"""
    return provider.Provider(
        f"{subscription_id}-provider",
        subscription_id=subscription_id,
    )

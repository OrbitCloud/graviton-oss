from typing import Optional, Sequence, Union

import pulumi


def fmt_name(v: Union[str, pulumi.Output[str], Sequence], sep: Optional[str] = "-") -> str:
    def format(v):
        return v.lower().replace(" ", sep).replace("_", sep).replace(".", sep)

    if isinstance(v, Sequence) and not isinstance(v, str):
        return "-".join([format(str(n)) for n in v])
    return format(v)

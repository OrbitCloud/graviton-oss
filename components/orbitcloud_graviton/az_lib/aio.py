import asyncio
import functools
from typing import Awaitable, Callable, ParamSpec, TypeVar

import pulumi

R = TypeVar("R")
P = ParamSpec("P")


def in_event_loop(_func: Callable[P, R]) -> Callable[P, Awaitable[R]]:
    @functools.wraps(wrapped=_func)
    async def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        return await asyncio.get_event_loop().run_in_executor(
            executor=None, func=functools.partial(_func, *args, **kwargs)
        )

    return wrapped


def async_output(_func: Callable[P, Awaitable[R]]) -> Callable[P, pulumi.Output[R]]:
    @functools.wraps(wrapped=_func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> pulumi.Output[R]:
        return pulumi.Output.from_input(val=_func(*args, **kwargs))

    return wrapped

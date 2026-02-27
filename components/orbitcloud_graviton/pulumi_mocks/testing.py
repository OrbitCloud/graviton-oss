"""Provides mock capabilities.

Usage:

`test_infra.py`
```
from pulumi_meltano.mocks import set_mocks

mock_settings = {"project:deployment_name": "mock"}
set_mocks(mock_settings)

# It's important to import other modules _after_ the mocks are defined.
import pulumi
...

def test_something():
    ...
```

"""

import asyncio
import json
import sys
from os import environ
from typing import Any

import pulumi


class MyPulumiMocks(pulumi.runtime.Mocks):
    """From https://www.pulumi.com/docs/guides/testing/unit/"""

    def new_resource(self, args: pulumi.runtime.MockResourceArgs) -> list[Any]:
        return [args.name + "_id", args.inputs]

    def call(self, args: pulumi.runtime.MockCallArgs) -> dict[Any, Any]:  # pyright: ignore
        return {}


def mock_pulumi_settings(settings: dict) -> None:
    """Mock Pulumi settings.

    https://github.com/pulumi/pulumi/issues/4472#issuecomment-1015818376
    """
    pulumi_settings: dict[str, str] = {}
    for key, val in settings.items():
        pulumi_settings[key] = val
    pulumi_settings_str = json.dumps(pulumi_settings)
    environ["PULUMI_CONFIG"] = pulumi_settings_str


def set_mocks(settings: dict | None = None) -> None:
    """Set up Pulumi mocks.

    Args:
        settings: (Optional.) A dictionary of settings to their values.
    """
    if settings:
        mock_pulumi_settings(settings)

    # Python 3.14+ requires explicit event loop creation
    if sys.version_info >= (3, 14):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, need to create one for the main thread
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # No event loop at all, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

    pulumi.runtime.set_mocks(
        MyPulumiMocks(), project="mock-project", preview=False, organization="mock-org"
    )

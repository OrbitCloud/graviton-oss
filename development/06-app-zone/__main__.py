"""Graviton Example: Container App Environment (App Zone)"""

import os

from orbitcloud_graviton.app_zone import deploy

if __name__ == "__main__":
    if os.environ.get("PULUMI_DEBUG") == "true":
        import debugpy  # type: ignore

        debugpy.listen(5678)
        debugpy.wait_for_client()
    deploy()

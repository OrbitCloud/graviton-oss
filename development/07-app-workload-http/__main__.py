"""Graviton Example: App Workload — HTTP-triggered Container App"""

import os

from orbitcloud_graviton.app_workload import deploy

if __name__ == "__main__":
    if os.environ.get("PULUMI_DEBUG") == "true":
        import debugpy  # type: ignore

        debugpy.listen(5678)
        debugpy.wait_for_client()
    deploy()

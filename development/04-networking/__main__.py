"""Graviton Example: Hub-Spoke Network"""

import os

from orbitcloud_graviton.hubspoke import deploy_hub_spoke

if __name__ == "__main__":
    if os.environ.get("PULUMI_DEBUG") == "true":
        import debugpy  # type: ignore

        debugpy.listen(5678)
        debugpy.wait_for_client()
    deploy_hub_spoke()

"""Graviton Example: Azure Firewall"""

import os

from orbitcloud_graviton.firewall import deploy_firewall

if __name__ == "__main__":
    if os.environ.get("PULUMI_DEBUG") == "true":
        import debugpy  # type: ignore

        debugpy.listen(5678)
        debugpy.wait_for_client()
    deploy_firewall()

"""Graviton Example: Landing Zone — Log Analytics, Key Vault, Container Registry"""

import os

from orbitcloud_graviton.landing_zone import deploy_landing_zone

if __name__ == "__main__":
    if os.environ.get("PULUMI_DEBUG") == "true":
        import debugpy  # type: ignore

        debugpy.listen(5678)
        debugpy.wait_for_client()
    deploy_landing_zone()

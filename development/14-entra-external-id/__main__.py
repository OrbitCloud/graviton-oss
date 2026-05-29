"""Graviton Example: Entra External ID (B2C) tenant"""

import os

from orbitcloud_graviton.entra_external_id import deploy

if __name__ == "__main__":
    if os.environ.get("PULUMI_DEBUG") == "true":
        import debugpy  # type: ignore

        debugpy.listen(5678)
        debugpy.wait_for_client()
    deploy()

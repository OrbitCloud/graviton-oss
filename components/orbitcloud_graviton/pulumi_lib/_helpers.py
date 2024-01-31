from typing import Any, List

import yaml


def print_pulumi_esc_oidc_yaml(args: List[Any]):
    client_id, tenant_id, subscription_id = args

    yaml_structure = {
        "values": {
            "azure": {
                "login": {
                    "fn::open::azure-login": {
                        "clientId": client_id,
                        "tenantId": tenant_id,
                        "subscriptionId": subscription_id,
                        "oidc": True,
                    }
                }
            },
            "environmentVariables": {
                "ARM_USE_OIDC": "true",
                "ARM_CLIENT_ID": "${azure.login.clientId}",
                "ARM_TENANT_ID": "${azure.login.tenantId}",
                "ARM_OIDC_TOKEN": "${azure.login.oidc.token}",
                "ARM_SUBSCRIPTION_ID": "${azure.login.subscriptionId}",
            },
            "pulumniConfig": {
                "azure-native": {
                    "location": "northeurope",
                    "tenantId": "${azure.login.tenantId}",
                    "subscriptionId": "${azure.login.subscriptionId}",
                },
                "azuread": {"tenantId": "${azure.login.tenantId}"},
            },
        }
    }

    print(yaml.dump(yaml_structure, sort_keys=False))

from typing import Any, List, Optional, Sequence, Union

import pulumi
import yaml


def fmt_name(v: Union[str, pulumi.Output[str], Sequence], sep: Optional[str] = "-") -> str:
    def format(v):
        return v.lower().replace(" ", sep).replace("_", sep).replace(".", sep)

    if isinstance(v, Sequence) and not isinstance(v, str):
        return "-".join([format(str(n)) for n in v])
    return format(v)


def print_pulumi_esc_oidc_yaml(args: List[Any]) -> None:
    client_id, tenant_id, subscription_id = args

    yaml_structure = {
        "values": {
            "azure": {
                "login": {
                    "fn::open::azure-login": {
                        "clientId": str(client_id),
                        "tenantId": str(tenant_id),
                        "subscriptionId": str(subscription_id),
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
            "pulumiConfig": {
                "azure-native:location": "northeurope",
                "azure-native:tenantId": "${azure.login.tenantId}",
                "azure-native:subscriptionId": "${azure.login.subscriptionId}",
                "azuread:tenantId": "${azure.login.tenantId}",
            },
        }
    }

    print(yaml.dump(yaml_structure, sort_keys=False))

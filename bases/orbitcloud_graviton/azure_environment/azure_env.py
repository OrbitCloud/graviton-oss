from typing import Any, Optional

import pulumi
from pydantic import Field

from orbitcloud_graviton.az_iam.assignment import IamAssignmentConfig
from orbitcloud_graviton.entra.entra_app import EntraApp, EntraAppConfig
from orbitcloud_graviton.entra.oidc_providers import PulumiOIDCCredentials
from orbitcloud_graviton.pulumi.esc_env import PulumiEscEnv
from orbitcloud_graviton.pulumi_lib.azure_base import (
    AzureStack,
    EntraStack,
    get_azure_stack,
    get_entra_stack,
)
from orbitcloud_graviton.pulumi_lib.config import PulumiConfig
from orbitcloud_graviton.pulumi_lib.stack_schema import generate_stack_schema


class AzureEnvironmentConfig(PulumiConfig):
    imports: Optional[list[str]] = None
    pulumi_config: Optional[dict[str, Any]] = Field(default_factory=dict)
    environment_variables: Optional[dict[str, Any]] = Field(default_factory=dict)
    azure_permissions: Optional[list[IamAssignmentConfig]] = None


def deploy() -> None:
    stack: AzureStack = get_azure_stack()
    entra: EntraStack = get_entra_stack()

    generate_stack_schema(model=AzureEnvironmentConfig, output_file=".stack_schema.json")

    config: AzureEnvironmentConfig = AzureEnvironmentConfig.model_validate(obj={})

    """
    Create an Entra App and configure Pulumi ESC OIDC credentials
    """
    esc_app: EntraApp = EntraApp(
        stack=stack.model_copy(update={"exports_prefix": "pulumi"}),
        entra=entra,
        config=EntraAppConfig(
            name="pulumi",
            federated_credentials=PulumiOIDCCredentials(
                organization=pulumi.get_organization()
            ).credentials(),
        ),
    )

    """
    Assign Default Azure permissions

    Additional permissions can be added via azure_permissions in stack config
    """
    azure_permissions: list[IamAssignmentConfig] = config.azure_permissions or []
    esc_app.azure_permissions(
        assignments=azure_permissions
        + [
            IamAssignmentConfig(
                name_prefix="pulumi",
                role=role,
                scope=f"/subscriptions/{stack.subscription_id}",
            )
            for role in [
                "Contributor",
                "Key Vault Secrets Officer",
                "Role Based Access Control Administrator",
            ]
        ]
    )

    """
    Pulumi Config exports

    Additional configuratios can be added via pulumi_config in stack config
    """
    pulumi_config: dict[str, Any] = (config.pulumi_config or {}) | {
        "azure-native:tenantId": "${azure.login.tenantId}",
        "azure-native:subscriptionId": "${azure.login.subscriptionId}",
        "azuread:tenantId": "${azure.login.tenantId}",
        "environment": {
            "resource_group_name": stack.resource_group.name,
            "pulumi_esc_app": {
                "app_client_id": esc_app.app.client_id,
                "service_principal_id": esc_app.service_principal.id,
            },
            "tags": {
                "Environment": stack.env,
            },
        },
    }

    """
    Environment Variable exports

    Additional environment variables can be added via environment_variables in stack config
    """
    env_vars: dict[str, str] = (config.environment_variables or {}) | {
        "ARM_USE_OIDC": "true",
        "ARM_CLIENT_ID": "${azure.login.clientId}",
        "ARM_TENANT_ID": "${azure.login.tenantId}",
        "ARM_OIDC_TOKEN": "${azure.login.oidc.token}",
        "ARM_SUBSCRIPTION_ID": "${azure.login.subscriptionId}",
    }

    PulumiEscEnv(
        env_name=stack.env,
        input={
            "imports": config.imports,
            "azure": {
                "login": {
                    "fn::open::azure-login": {
                        "clientId": esc_app.app.client_id,
                        "tenantId": str(object=stack.tenant_id),
                        "subscriptionId": str(object=stack.subscription_id),
                        "oidc": True,
                    }
                }
            },
            "pulumi_config": pulumi_config,
            "environment_variables": env_vars,
        },
    )

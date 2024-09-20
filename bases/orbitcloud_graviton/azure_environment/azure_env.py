from typing import Any, Optional

import pulumi
from pydantic import Field

from orbitcloud_graviton.az_iam.assignment import IamAssignmentConfig
from orbitcloud_graviton.entra.entra_app import EntraApp, EntraAppConfig
from orbitcloud_graviton.entra.oidc_providers import PulumiEscOidcProvider
from orbitcloud_graviton.pulumi.esc_env import PulumiEnv, PulumiEnvConfig
from orbitcloud_graviton.pulumi_lib.azure_base import (
    AzureStack,
    EntraStack,
    get_azure_stack,
    get_entra_stack,
)
from orbitcloud_graviton.pulumi_lib.config import PulumiConfig
from orbitcloud_graviton.pulumi_lib.stack_schema import generate_stack_schema


class AzureEnvironmentConfig(PulumiConfig):
    esc_env_name: Optional[str] = None
    imports: Optional[list[str]] = None
    pulumi_config: Optional[dict[str, Any]] = Field(default_factory=dict)
    environment_variables: Optional[dict[str, Any]] = Field(default_factory=dict)
    azure_permissions: Optional[list[IamAssignmentConfig]] = None
    allowed_in_childs: bool = False


def deploy() -> None:
    stack: AzureStack = get_azure_stack()
    entra: EntraStack = get_entra_stack()

    generate_stack_schema(model=AzureEnvironmentConfig, output_file=".stack_schema.json")

    config: AzureEnvironmentConfig = AzureEnvironmentConfig.model_validate(obj={})

    esc_provider = PulumiEscOidcProvider(
        organization=pulumi.get_organization(),
        environment_name=config.esc_env_name or stack.env,
        allowed_in_childs=config.allowed_in_childs,
    )

    """
    Create an Entra App and configure Pulumi ESC OIDC credentials
    """
    esc_app: EntraApp = EntraApp(
        stack=stack.model_copy(update={"exports_prefix": "pulumi"}),
        entra=entra,
        config=EntraAppConfig(
            name="pulumi",
            federated_credentials=esc_provider.credentials(),
            entra_roles=["Cloud Application Administrator"],
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
    pulumi_config: dict[str, Any] = (
        # Azure OIDC Pulumi Config
        esc_provider.azure_pulumi_config()
        # Environment Config
        | {
            "azure-native:location": stack.location,
            "env": stack.env,
            "azure_environment": {
                "resource_group_name": stack.resource_group.name,
                "pulumi_esc_app": {
                    "name": esc_app.app.display_name,
                    "app_client_id": esc_app.app.client_id,
                    "app_object_id": esc_app.app.object_id,
                    "service_principal_id": esc_app.service_principal.id,
                    "service_principal_object_id": esc_app.service_principal.object_id,
                },
                "tags": {
                    "Environment": stack.env,
                },
            },
        }
        # Additional user defined pulumi config
        | (config.pulumi_config or {})
    )

    """
    Environment Variable exports

    Additional environment variables can be added via environment_variables in stack config
    """
    env_vars: dict[str, str] = (config.environment_variables or {}) | esc_provider.azure_env_vars()

    PulumiEnv(
        config=PulumiEnvConfig(env_name=config.esc_env_name or stack.env),
        input={
            "env_name": config.esc_env_name or stack.env,
            "imports": config.imports,
            "values": {
                "azure": esc_provider.azure_login(stack=stack, client_id=esc_app.app.client_id),
                "pulumi_config": pulumi_config,
                "environment_variables": env_vars,
            },
        },
    )

from orbitcloud_graviton.entra.entra_app import EntraApp, EntraAppConfig
from orbitcloud_graviton.pulumi_lib import (
    AzureStack,
    EntraStack,
    PulumiConfig,
    generate_stack_schema,
    get_azure_stack,
    get_entra_stack,
)


class OauthAppsConfig(PulumiConfig):
    oauth_apps: list[EntraAppConfig] | None = None


def deploy() -> None:
    generate_stack_schema(model=OauthAppsConfig, output_file=".stack_schema.json")

    config: OauthAppsConfig = OauthAppsConfig.model_validate({})
    entra_config: EntraStack = EntraStack.model_validate({})

    # Get Azure Stack and export resource group
    stack: AzureStack = get_azure_stack()
    entra_config: EntraStack = get_entra_stack()

    apps: dict[str, EntraApp] = {
        app.name: EntraApp(
            stack=stack.model_copy(update={"skip_exports": True}),
            entra=entra_config,
            config=app,
        )
        for app in config.oauth_apps or []
    }

    stack.export(
        exports={
            "oauth_apps": {
                app_name: {
                    "tenant_id": str(entra_config.tenant_id),
                    "client_id": app.service_principal.client_id,
                    "endpoints": {
                        "auth": f"https://login.microsoftonline.com/{entra_config.tenant_id}/oauth2/v2.0/authorize",
                        "token": f"https://login.microsoftonline.com/{entra_config.tenant_id}/oauth2/v2.0/token",
                    },
                    "client_secrets": {
                        secret_name: secret.value
                        for secret_name, secret in app.client_credentials.items()
                    }
                    if app.client_credentials
                    else None,
                    "redirect_uris": app.app.web.redirect_uris,
                    "app_roles": app.app.app_roles.apply(
                        func=lambda roles: (
                            [
                                {
                                    "id": role.id,
                                    "display_name": role.display_name,
                                    "value": role.value,
                                    "description": role.description,
                                }
                                for role in roles
                            ]
                            if roles
                            else None
                        )
                    ),
                }
                for app_name, app in apps.items()
            }
        }
    )

"""
(WIP) Base for top-level global "Customer / Azure Tenant" configurations

Creates a Pulumi ESC environment config to be used in downstream environments/projects regardless
of subscription, env etc..

What settings are currently being set _to be consumed_ downstream?
- Pinning tenantId in pulumi_config for downstream projects to avoid accidental provisioning
  resources in wrong tenants
- Setting default configured location/region for Azure resources
- Defining resource tagging rules for downstream environments to enforce
- Setting default tags to be globally included in all downstream resources


Possible features to be added:

- Entra user/group management:
    - User creation/invitations
    - Provisioning Entra groups and configuring group memberships
    - Entra role assignments to groups/users
    - This could include creating some default groups for different job roles:
        - tenant-admins
        - developers
        - infra-developers
        - infra-admins
        - database-admins

- Configuring Entra security settings:
    - Conditional Access Policies

- Management of Azure subscriptions:
    - Management groups
    - Permissions / Role assignment to Azure users/groups
    - Azure Policy (azure-native.authorization.PolicySet[Definition|DefinitionAtManagementGroup ?)

- PIM
    - Entra
        - Seems to be waiting to be released in the terraform provider (which pulumi-azuread is based off):
            https://github.com/hashicorp/terraform-provider-azuread/issues/68
    - Azure
        - Are these the correct azure-native resources?
            https://www.pulumi.com/registry/packages/azure-native/api-docs/managedservices/registrationassignment/
            https://www.pulumi.com/registry/packages/azure-native/api-docs/managedservices/registrationdefinition/

- Tenant / account posture/monitoring:
    - Security alerts (azure-native.securityinsights.AutomationRule ?)
    - Billing alerts for threshold and failed payment alerts (azure-native.consumption.Budget)

- Environments
    - Configuration for bases?
        - e.g. in which env/project/stack will the network hub be located?

"""

from typing import Any, Literal

import pulumi
from pydantic import BaseModel

from orbitcloud_graviton.az_network.types import PublicIPv4Network
from orbitcloud_graviton.pulumi.esc_env import PulumiEnv, PulumiEnvConfig, PulumiEnvConfigValues
from orbitcloud_graviton.pulumi_lib.azure_base import (
    EntraStack,
    get_entra_stack,
)
from orbitcloud_graviton.pulumi_lib.config import PulumiConfig
from orbitcloud_graviton.pulumi_lib.stack_schema import generate_stack_schema


class Customer(BaseModel):
    """
    Customer information - WIP - to be extended...
    """

    name: str
    active: bool = True


class PulumiDefaults(BaseModel):
    """
    Relevant or not? - Not sure yet..
    """

    organization: str = pulumi.get_organization()


class ResourceArgs(BaseModel):
    """
    Resource arguments for Azure resources provisioned in downstream environments

    WIP
    """

    parameter: str
    value: dict[Literal["default", "always"], Any]


class ResourceArgsDefaults(BaseModel):
    """
    Resource argument defaults or additions for Azure resources provisioned in downstream
    environments (not implemented yet)

    WIP

    f.x.:

        # Automatically add specific owners to all Azure AD applications
        azuread:Application:
            owners:
                always:
                    entra_group: app_admins

        # Could be used to enforce specific settings for all Azure SQL databases
        # although Pulumi Policy might be a better fit for this...
        azure-native:databases:SqlDatabase:
            public_network_access:
                default: Disabled

        Or special settings - which would have to be implemented on a per-resource parameter-name basis

    Maybe the Azure PSRule model should be used instead?
    """

    resource_type: str
    defaults: dict[str, Any]


class TaggingRules(BaseModel):
    """
    Tagging rules which downstream projects can use to enforce tagging rules
    https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/azure-best-practices/resource-tagging

    On what level should we enforce tagging rules?
    - IaC code
    - Pulumi Policy
    - Azure Policy
    - all/subset of the above?
    """

    required_tags: list[str]
    optional_tags: list[str]


class Subscription(BaseModel):
    subscription_id: str
    subscription_name: str
    env: str

    security_contact: str | None = None  # (See azure-native.security.SecurityContact)
    billing_alert_monthly_threshold_usd: int | None = None

    # TODO: validate that subscription_name matches the name of the retreived subscription_id
    # So that we can avoid having to eye-ball whether subscription_id is correct in downstream projects
    # @model_validator(mode="after")
    # def subscription_name_match(m: "Subscription") -> "Subscription":
    #     ...
    #     return m


class Globals(BaseModel):
    """
    Global Pulumi configurations accessible in downstream environments
    """

    pulumi: PulumiDefaults = PulumiDefaults()
    location: str = "northeurope"

    resource_name_prefix: str | None = None

    # trusted_locations: Country eða CIDR spaces...

    # Should use key/values for describing the values
    ip_allow_list: list[PublicIPv4Network] | None = None

    tags: dict[str, str] | None = None
    tagging_rules: TaggingRules | None = TaggingRules(
        required_tags=[
            "Env",
            "WorkloadName",
            "DataClassification",
            "BusinessCriticality",
            "BackupPolicy",  # E.g. N/A - daily/30days & monthly/365days
            "OpsTeam",  # E.g. Orbit Cloud ehf.
            "OpsResponsibility"  # E.g. platform, application, data
            "OpsContact",  # E.g. Email address / Phone number / Slack handle
            "OpsMonitorAlerts",  # E.g. N/A
            "OpsSLA",  # N/A / 24x7 / 8x5
        ],
        optional_tags=[
            "ProvisionType",  # IaC
            "Owner",  # Business owner or workload owner
        ],
    )

    resource_args: list[ResourceArgsDefaults] | None = None


class AzureTenantConfig(PulumiConfig):
    env: str
    customer: Customer
    esc: PulumiEnvConfig
    globals: Globals = Globals()


def deploy() -> None:
    # stack: AzureStack = get_azure_stack()
    entra: EntraStack = get_entra_stack()

    generate_stack_schema(model=AzureTenantConfig, output_file=".stack_schema.json")

    config: AzureTenantConfig = AzureTenantConfig.model_validate(obj={})

    """
    Pulumi Config exports

    Additional configuratios can be added via pulumi_config in stack config
    """
    pulumi_config: dict[str, Any] = {
        "azure-native:location": config.globals.location,
        "azure-native:tenantId": str(object=entra.tenant_id),
        "azuread:tenantId": str(object=entra.tenant_id),
        "globals": config.globals.model_dump(exclude_none=True),
    }

    """
    Environment Variable exports

    Additional environment variables can be added via environment_variables in stack config
    """
    env_vars: dict[str, str] = {
        "ARM_TENANT_ID": str(object=entra.tenant_id),
    } | (config.esc.values.environment_variables or {})

    """
    Pulumi ESC environment config
    """
    PulumiEnv(
        config=PulumiEnvConfig(
            env_name=config.env,
            imports=config.esc.imports,
            values=PulumiEnvConfigValues(
                pulumi_config=pulumi_config,
                environment_variables=env_vars,
            ),
        ),
        input={},
    )

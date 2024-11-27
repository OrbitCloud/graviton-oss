from dataclasses import dataclass
from enum import Enum

import pulumi
from pulumi_azure_native import insights, operationalinsights, resources, web

from orbitcloud_graviton.az_lib import resource_namer
from orbitcloud_graviton.az_monitor import diagnostic_setting


class PlanSkuTiers(str, Enum):
    P = "PremiumV3"
    E = "ElasticPremium"
    S = "Standard"
    B = "Basic"
    F = "Free"


class PlanSkuNames(str, Enum):
    P0V3 = "P0V3"
    P1V3 = "P1V3"
    P2V3 = "P2V3"
    P3V3 = "P3V3"
    P1MV3 = "P1MV3"
    P2MV3 = "P2MV3"
    P3MV3 = "P3MV3"
    P4MV3 = "P4MV3"
    P5MV3 = "P5MV3"
    EP1 = "EP1"
    EP2 = "EP2"
    EP3 = "EP3"
    S1 = "S1"
    S2 = "S2"
    S3 = "S3"
    B1 = "B1"
    B2 = "B2"
    B3 = "B3"
    F1 = "F1"

    def __str__(self) -> str:
        return self.value

    def tier(self) -> str:
        return PlanSkuTiers(self.value[0])


@dataclass(kw_only=True, frozen=True)
class AppServicePlanStackSchema:
    plan_per_site_scaling: bool | None = True
    plan_sku: str | None = PlanSkuNames.P0V3
    plan_instance_count_default: int | None = 2
    plan_instance_count_min: int | None = 2
    plan_instance_count_max: int | None = 2
    plan_zone_redundant: bool | None = False
    plan_log_workspace_ref: str | None = None

    @property
    def plan_sku_args(self) -> web.SkuDescriptionArgs:
        sku_name: str = PlanSkuNames(self.plan_sku)
        sku_tier: str = sku_name.tier()

        if sku_tier is None or sku_name is None:
            raise ValueError(f"Invalid SKU tier: {sku_tier} or SKU name: {sku_name}")

        return web.SkuDescriptionArgs(
            name=sku_name,
            tier=sku_tier,
            sku_capacity=web.SkuCapacityArgs(
                default=self.plan_instance_count_default,
                minimum=self.plan_instance_count_min,
                maximum=self.plan_instance_count_max,
            ),
        )


def az_appservice_plan(
    workload_name: str,
    env: str,
    location: str,
    resource_group: resources.ResourceGroup,
    kind: str | None = "Linux",
    per_site_scaling: bool | None = True,
    zone_redundant: bool | None = False,
    sku: web.SkuDescriptionArgs | None = web.SkuDescriptionArgs(
        name="P0V3",
        tier="PremiumV3",
        sku_capacity=web.SkuCapacityArgs(
            default=2,
            maximum=2,
            minimum=2,
        ),
    ),
    log_workspace: operationalinsights.Workspace | None = None,
    tags: dict[str, str] | None = None,
    opts: pulumi.ResourceOptions | None = None,
) -> web.AppServicePlan:
    plan_name: str = resource_namer(
        resource_type=web.AppServicePlan,
        workload_name=workload_name,
        env=env,
        location=location,
    )

    plan: web.AppServicePlan = web.AppServicePlan(
        resource_name=plan_name,
        location=location,
        tags=tags,
        resource_group_name=resource_group.name,
        kind=kind,
        reserved=True,
        per_site_scaling=per_site_scaling,
        zone_redundant=zone_redundant,
        sku=sku,
        opts=opts,
    )

    if log_workspace:
        _az_appservice_plan_diagnostic(
            resource=plan,
            log_workspace=log_workspace,
        )

    return plan


def az_appservice_plan_from_config(
    config,
    resource_group: resources.ResourceGroup | None = None,
) -> web.AppServicePlan:
    if not resource_group and not config.resource_group:
        raise ValueError("Either resource_group or resource_group_name must be set")

    return az_appservice_plan(
        workload_name=config.workload_name,
        env=config.env,
        location=config.location,
        resource_group=config.resource_group,
        tags=config.tags,
        per_site_scaling=config.plan_per_site_scaling,
        zone_redundant=config.plan_zone_redundant,
        sku=config.plan_sku,
        log_workspace=config.plan_log_workspace,
    )


def _az_appservice_plan_diagnostic(
    resource: web.AppServicePlan,
    log_workspace: operationalinsights.Workspace,
) -> insights.DiagnosticSetting:
    settings = diagnostic_setting(
        resource=resource,
        log_workspace_id=log_workspace.id,
        metric_categories=["AllMetrics"],
        opts=pulumi.ResourceOptions(parent=resource),
    )
    return settings

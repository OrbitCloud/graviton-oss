from dataclasses import dataclass
from typing import Dict, Optional

import pulumi
from orbitcloud_graviton.az_lib import BaseConfig, resource_namer
from orbitcloud_graviton.az_monitor import az_diagnosticsetting
from pulumi_azure_native import insights, operationalinsights, resources, web


@dataclass
class AppServicePlanArgs(BaseConfig):
    per_site_scaling: Optional[bool] = True
    sku: Optional[web.SkuDescriptionArgs] = web.SkuDescriptionArgs(
        name="P0V3",
        tier="PremiumV3",
        sku_capacity=web.SkuCapacityArgs(
            default=2,
            maximum=2,
            minimum=2,
        ),
    )
    zone_redundant: Optional[bool] = True


@dataclass
class AppServicePlanElasticAzFuncArgs(BaseConfig):
    per_site_scaling: Optional[bool] = True
    sku: web.SkuDescriptionArgs = web.SkuDescriptionArgs(
        name="EP1",
        tier="ElasticPremium",
        sku_capacity=web.SkuCapacityArgs(
            default=2,
            maximum=2,
            minimum=2,
        ),
    )
    zone_redundant: Optional[bool] = True


def az_appservice_plan(
    workload_name: str,
    env: str,
    location: str,
    resource_group: resources.ResourceGroup,
    kind: Optional[str] = "Linux",
    per_site_scaling: Optional[bool] = True,
    zone_redundant: Optional[bool] = False,
    sku: Optional[web.SkuDescriptionArgs] = web.SkuDescriptionArgs(
        name="P0V3",
        tier="PremiumV3",
        sku_capacity=web.SkuCapacityArgs(
            default=2,
            maximum=2,
            minimum=2,
        ),
    ),
    log_workspace: Optional[operationalinsights.Workspace] = None,
    tags: Optional[Dict[str, str]] = None,
    opts: Optional[pulumi.ResourceOptions] = None,
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


def _az_appservice_plan_diagnostic(
    resource: web.AppServicePlan,
    log_workspace: operationalinsights.Workspace,
) -> insights.DiagnosticSetting:
    settings = az_diagnosticsetting(
        resource=resource,
        log_workspace=log_workspace,
        metric_categories=["AllMetrics"],
        opts=pulumi.ResourceOptions(parent=resource),
    )
    return settings

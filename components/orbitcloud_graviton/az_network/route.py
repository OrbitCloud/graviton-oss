from ipaddress import IPv4Address, IPv4Network
from typing import Literal

import pulumi
from pulumi import ComponentResource
from pulumi_azure_native import network
from pydantic import BaseModel, ConfigDict, model_validator

from orbitcloud_graviton.pulumi_lib import AzureStack


class RouteConfig(BaseModel):
    name: str
    address_prefix: IPv4Network
    next_hop_type: Literal[
        "VirtualNetworkGateway", "VnetLocal", "Internet", "VirtualAppliance", "None"
    ]
    next_hop_ip_address: IPv4Address | None = None

    @model_validator(mode="after")
    def validate_next_hop(m: "RouteConfig") -> "RouteConfig":
        if m.next_hop_type == "VirtualAppliance" and not m.next_hop_ip_address:
            raise ValueError("next_hop_ip_address is required for VirtualAppliance")
        return m


class RouteTableConfig(BaseModel):
    name: str
    routes: list[RouteConfig]
    disable_bgp_route_propagation: bool | None = False

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class RouteTable(ComponentResource):
    def __init__(
        self,
        stack: AzureStack,
        config: RouteTableConfig,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        self.stack: AzureStack = stack
        self.config: RouteTableConfig = config

        super().__init__(
            "Graviton:RouteTable",
            name=f"rt-{self.config.name}",
            props=None,
            opts=opts,
        )

        self._opts = pulumi.ResourceOptions.merge(
            opts1=opts,
            opts2=pulumi.ResourceOptions(parent=self),
        )

        self.route_table = self._create_route_table()
        self.routes = self._create_routes()

        self._outputs()

    def _create_route_table(self) -> network.RouteTable:
        return network.RouteTable(
            resource_name=self.stack.name_for(network.RouteTable, workload_name=self.config.name),
            route_table_name=self.stack.name_for(
                network.RouteTable, workload_name=self.config.name
            ),
            location=self.stack.location,
            resource_group_name=self.stack.resource_group.name,
            disable_bgp_route_propagation=self.config.disable_bgp_route_propagation,
            opts=self._opts,
        )

    def _create_routes(self) -> list[network.Route]:
        routes = []
        for i, route in enumerate(self.config.routes):
            r = network.Route(
                resource_name=f"{self.config.name}-{route.name}-{i}",
                route_name=route.name,
                route_table_name=self.route_table.name,
                resource_group_name=self.stack.resource_group.name,
                address_prefix=str(route.address_prefix),
                next_hop_type=route.next_hop_type,
                next_hop_ip_address=str(route.next_hop_ip_address)
                if route.next_hop_ip_address
                else None,
                opts=pulumi.ResourceOptions(parent=self.route_table),
            )
            routes.append(r)
        return routes

    def _outputs(self) -> None:
        self.register_outputs(
            outputs={
                "route_table": self.route_table,
                "routes": self.routes,
            }
        )

        self.stack.export(
            exports={
                f"route_table_{self.config.name}": {
                    "id": self.route_table.id,
                    "name": self.route_table.name,
                    "routes": [r.name for r in self.routes],
                }
            }
        )

from ipaddress import IPv4Address
from typing import Any

import pulumi
from pulumi import ComponentResource
from pulumi_azure_native.network import v20200601 as network
from pydantic import BaseModel, ConfigDict

from orbitcloud_graviton.az_lib.types import AzureIdRef, AzureResourceId
from orbitcloud_graviton.pulumi_lib import AzureStack

from .types import ARecord, CnameRecord, MxRecord, Record, TxtRecord


class PrivateDNSZoneConfig(BaseModel):
    name: str
    records: list[Record] | None = None
    linked_vnets: list[AzureIdRef] | None = None  # List of VNET IDs
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class PrivateDnsZone(ComponentResource):
    def __init__(
        self,
        stack: AzureStack,
        config: PrivateDNSZoneConfig,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        self.stack: AzureStack = stack
        self.config: PrivateDNSZoneConfig = config

        super().__init__(
            "Graviton:az_network:PrivateDnsZone",
            name=self.config.name,
            props=None,
            opts=opts,
        )

        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts1=opts, opts2=pulumi.ResourceOptions(parent=self)
        )
        self.zone: network.PrivateZone = self._zone()
        self.records: list[network.PrivateRecordSet] = self._records()
        self._outputs()

    def _zone(self) -> network.PrivateZone:
        if not isinstance(self.config.name, str):
            raise ValueError("DNS zone name must be a string")

        zone = network.PrivateZone(
            resource_name=self.config.name,
            private_zone_name=self.config.name,
            resource_group_name=self.stack.resource_group.name,
            location="Global",
            opts=self._opts,
        )

        if self.config.linked_vnets:
            for vnet in self.config.linked_vnets:
                v = AzureResourceId(str(vnet))
                network.VirtualNetworkLink(
                    resource_name=f"{v.resource_name}_{self.config.name}",  # type: ignore
                    virtual_network_link_name=v.resource_name,
                    resource_group_name=self.stack.resource_group.name,
                    location="Global",
                    private_zone_name=zone.name,
                    virtual_network=network.SubResourceArgs(id=v.id),
                    registration_enabled=False,
                    opts=pulumi.ResourceOptions.merge(
                        self._opts, pulumi.ResourceOptions(delete_before_replace=True)
                    ),
                )
        return zone

    def _records(self) -> list[network.PrivateRecordSet]:
        if self.config.records:
            return [self.record(record) for record in self.config.records]
        return []

    def record(self, record: Record) -> network.PrivateRecordSet:
        record_args = self._record_args(record)
        return network.PrivateRecordSet(
            resource_name=self.stack.name_for(
                resource_type=network.PrivateRecordSet,
                workload_name=f"{record.record_type}-{record.relative_name}-{self.config.name}".replace(
                    ".", "-"
                ).lower(),
            ),
            resource_group_name=self.stack.resource_group.name,
            private_zone_name=self.zone.name,
            relative_record_set_name=record.relative_name,
            record_type=record.record_type,
            ttl=record.ttl,
            **record_args,
            opts=pulumi.ResourceOptions.merge(self._opts, pulumi.ResourceOptions(parent=self.zone)),
        )

    def _record_args(self, record: Record) -> dict[str, Any]:
        if isinstance(record, ARecord):
            records = []
            for ip in record.ip_addresses:
                ip = str(ip) if isinstance(ip, IPv4Address) else ip
                records.append(network.ARecordArgs(ipv4_address=ip))
            return {
                "a_records": records,
            }
        if isinstance(record, CnameRecord):
            return {"cname_record": network.CnameRecordArgs(cname=record.value)}
        if isinstance(record, MxRecord):
            return {
                "mx_records": [
                    network.MxRecordArgs(preference=record.preference, exchange=record.exchange)
                ]
            }
        if isinstance(record, TxtRecord):
            return {"txt_records": [network.TxtRecordArgs(value=record.values)]}

        raise NotImplementedError(f"Record type {record.record_type} not implemented")

    def _outputs(self) -> None:
        self.register_outputs(
            outputs={
                "zone": self.zone,
                "records": self.records,
            }
        )
        self.stack.export(
            exports={
                "private_dns_zone": {
                    "id": self.zone.id,
                    "name": self.zone.name,
                }
            }
        )

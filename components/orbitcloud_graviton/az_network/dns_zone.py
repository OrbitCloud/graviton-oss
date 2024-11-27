from collections.abc import Sequence
from ipaddress import IPv4Address
from typing import Any

import pulumi
from pulumi_azure_native import Provider, network
from pydantic import BaseModel, ConfigDict, Field

from orbitcloud_graviton.az_lib.types import AzureIdRef, AzureResourceId
from orbitcloud_graviton.pulumi_lib import AzureStack
from orbitcloud_graviton.pulumi_lib.types import DomainName

from .types import ARecord, CnameRecord, MxRecord, NsRecord, Record, TxtRecord


class DnsZoneConfig(BaseModel):
    name: DomainName
    records: list[Record] | None = None

    parent_zone_id: AzureIdRef | None = Field(
        default=None, title="ID of a parent zone in which NS records will be created"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class DnsZone(pulumi.ComponentResource):
    def __init__(
        self,
        stack: AzureStack,
        config: DnsZoneConfig,
        dns_zone_id: str | pulumi.Output[str] | None = None,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        self.stack: AzureStack = stack
        self.config: DnsZoneConfig = config

        super().__init__(
            "Graviton:az_network:DnsZone",
            name=f"dns-{self.config.name}".replace(".", "-"),
            props=None,
            opts=opts,
        )
        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts1=opts, opts2=pulumi.ResourceOptions(parent=self)
        )

        self.dns_zone_id: str | pulumi.Output[str] | None = dns_zone_id
        self.zone: network.Zone = self._zone()
        self.records: list[network.RecordSet] = self._records()
        self.parent_zone_ns_records = self._parent_zone_ns_records()

        self._outputs()

    def _zone(self) -> network.Zone:
        if self.dns_zone_id:
            zone = network.Zone.get(
                resource_name="dns-zone-reference",
                id=self.dns_zone_id,
                opts=self._opts,
            )

            return zone

        if not isinstance(self.config.name, str):
            raise ValueError("DNS zone name must be a string")

        return network.Zone(
            resource_name=self.stack.name_for(
                resource_type=network.Zone, workload_name=self.config.name.replace(".", "-")
            ),
            zone_name=self.config.name,
            resource_group_name=self.stack.resource_group.name,
            location="global",
            opts=self._opts,
        )

    def _records(self) -> list[network.RecordSet]:
        if self.config.records:
            return [self.record(record) for record in self.config.records]
        return []

    def record(self, record: Record) -> network.RecordSet:
        record_args = self._record_args(record)
        return network.RecordSet(
            resource_name=self.stack.name_for(
                resource_type=network.RecordSet,
                workload_name=f"{record.record_type}-{record.relative_name}-{self.config.name}".replace(
                    ".", "-"
                ).lower(),
            ),
            resource_group_name=self.stack.resource_group.name,
            zone_name=self.zone.name,
            relative_record_set_name=record.relative_name,
            record_type=record.record_type,
            ttl=record.ttl,
            **record_args,
            opts=pulumi.ResourceOptions.merge(
                opts1=self._opts, opts2=pulumi.ResourceOptions(parent=self.zone)
            ),
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
        if isinstance(record, NsRecord):
            return {"ns_records": [network.NsRecordArgs(nsdname=ns) for ns in record.ns_records]}
        if isinstance(record, MxRecord):
            return {
                "mx_records": [
                    network.MxRecordArgs(preference=record.preference, exchange=record.exchange)
                ]
            }
        if isinstance(record, TxtRecord):
            return {"txt_records": [network.TxtRecordArgs(value=record.values)]}

        raise NotImplementedError(f"Record type {record.record_type} not implemented")

    def _parent_zone_ns_records(self) -> list[network.RecordSet] | None:
        if self.config.parent_zone_id:
            parent_zone = AzureResourceId(str(self.config.parent_zone_id))
            if not parent_zone.resource_name:
                raise ValueError("Parent zone ID must include a resource name")
            opts = self._opts
            if (
                parent_zone.subscription_id
                and parent_zone.subscription_id != self.stack.subscription_id
            ):
                opts = pulumi.ResourceOptions.merge(
                    opts,
                    pulumi.ResourceOptions(
                        provider=Provider(
                            resource_name="parent-zone-provider",
                            subscription_id=str(parent_zone.subscription_id),
                        )
                    ),
                )

            ns_servers: pulumi.Output[Sequence[str]] = self.zone.name_servers
            network.RecordSet(
                resource_name=self.stack.name_for(
                    resource_type=network.RecordSet,
                    workload_name=f"parent-ns-{self.config.name}".replace(".", "-"),
                ),
                resource_group_name=parent_zone.resource_group_name,
                zone_name=parent_zone.resource_name,
                relative_record_set_name=self.config.name.removesuffix(
                    parent_zone.resource_name
                ).strip("."),
                record_type="NS",
                ns_records=[
                    network.NsRecordArgs(nsdname=ns_servers[0]),
                    network.NsRecordArgs(nsdname=ns_servers[1]),
                    network.NsRecordArgs(nsdname=ns_servers[2]),
                    network.NsRecordArgs(nsdname=ns_servers[3]),
                ],
                ttl=3600,
                opts=opts,
            )

    def _outputs(self) -> None:
        self.register_outputs(
            outputs={
                "zone": self.zone,
                "records": self.records,
            }
        )
        self.stack.export(
            exports={
                "dns_zone": {
                    "id": self.zone.id,
                    "name": self.zone.name,
                }
            }
        )

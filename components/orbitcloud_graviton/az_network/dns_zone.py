from typing import Any, List, Optional

import pulumi
from pulumi_azure_native import network
from pydantic import BaseModel, ConfigDict, Field

from orbitcloud_graviton.az_lib.types import AzureIdRef
from orbitcloud_graviton.pulumi_lib import AzureBase
from orbitcloud_graviton.pulumi_lib.types import DomainName

from .types import ARecord, CnameRecord, MxRecord, NsRecord, Record, TxtRecord


class DnsZoneConfig(BaseModel):
    name: DomainName
    records: Optional[List[Record]] = None

    child_zones: Optional[AzureIdRef] = Field(
        default=None, title="ID of a parent zone in which NS records will be created"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class DnsZone(pulumi.ComponentResource):
    def __init__(
        self,
        stack: AzureBase,
        config: DnsZoneConfig,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        self.stack: AzureBase = stack
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

        self.zone: network.Zone = self._zone()
        self.records: List[network.RecordSet] = self._records()

        self._outputs()

    def _zone(self) -> network.Zone:
        return network.Zone(
            resource_name=self.stack.name_for(
                resource_type=network.Zone, workload_name=self.config.name.replace(".", "-")
            ),
            zone_name=self.config.name,
            resource_group_name=self.stack.resource_group.name,
            location="global",
            opts=self._opts,
        )

    def _records(self) -> List[network.RecordSet]:
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
            zone_name=self.config.name,
            relative_record_set_name=record.relative_name,
            record_type=record.record_type,
            ttl=record.ttl,
            **record_args,
            opts=self._opts._merge_instance(pulumi.ResourceOptions(parent=self.zone)),
        )

    def _record_args(self, record: Record) -> dict[str, Any]:
        if isinstance(record, ARecord):
            return {
                "a_records": [
                    network.ARecordArgs(ipv4_address=str(ip)) for ip in record.ip_addresses
                ]
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
            return {"txt_records": [network.TxtRecordArgs(value=txt) for txt in record.values]}
        raise NotImplementedError(f"Record type {record.record_type} not implemented")

    def _outputs(self) -> None:
        self.register_outputs(
            outputs={
                "zone": self.zone,
                "records": self.records,
            }
        )
        pulumi.export(
            "dns_zone",
            value={
                "id": self.zone.id,
                "name": self.zone.name,
            },
        )

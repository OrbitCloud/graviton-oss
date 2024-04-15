import re
from typing import Optional

from pydantic import BaseModel, ConfigDict

from orbitcloud_graviton.pulumi_lib.azure_base import AzureStack
from orbitcloud_graviton.pulumi_lib.types import DomainName

from .helpers import fmt_name, location_abbr
from .metadata.azure import _azure_resource_meta
from .naming import ResourceNameRule


class PulumiResource(BaseModel):
    package: str
    namespace: str
    resource_class: str

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class AzureResourceMetadata(BaseModel):
    naming: ResourceNameRule
    namespace: Optional[str] = None
    resource_type: Optional[str] = None
    sub_resource_name: Optional[str] = None
    public_dns_zone: Optional[DomainName] = None
    private_dns_zone: Optional[DomainName] = None
    pulumi_resource: PulumiResource

    def autoname(
        self,
        stack: AzureStack,
        workload_name: Optional[str] = None,
        separator: Optional[str] = "-",
        instance_number: Optional[str] = "01",
    ) -> str:
        # Return prefix-{workload_name}-{env}-{location}-{instance_number}
        # In accordance with ResourceNameRule
        # alphanumeric - remove non-alphanumeric characters and convert to title case
        # lowercase - convert to lowercase
        # max_length - truncate to max_length

        workload_name = workload_name or stack.workload_name
        instance_number = "" if instance_number is None else instance_number

        if self.naming.alphanumeric:
            workload_name = fmt_name(v=workload_name, sep="", case="title")
            separator = ""

        parts: list[str | int] = [
            self.naming.prefix,
            workload_name,
            stack.env,
            location_abbr(location=stack.location),
            instance_number,
        ]

        return fmt_name(
            v=parts,
            sep=separator,
            case="title" if self.naming.alphanumeric and not self.naming.lowercase else "lower",
        )

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


def _pulumi_resource_signature(obj) -> PulumiResource:
    """
    Return the package, namespace, and resource name of a Pulumi resource class. i.e.
        package: pulumi_azure_native
        namespace: network
        resource: VirtualNetwork
    """
    signature = obj.__module__
    # Remove API version from module name
    if re.match(pattern=r"v\d{8}", string=signature.split(".")[-2]):
        signature: str = ".".join(signature.split(".")[:-2] + signature.split(".")[-1:])

    package: str = signature.split(".")[0]
    namespace: str = signature.split(".")[1]

    resource: str = obj.__name__ if hasattr(obj, "__name__") else obj.__class__.__name__

    return PulumiResource(
        package=package,
        namespace=namespace,
        resource_class=resource,
    )


def resource_meta(obj: object) -> AzureResourceMetadata:
    """
    Return the resource options for a given resource signature.
    """

    pulumi_resource: PulumiResource = _pulumi_resource_signature(obj=obj)

    resource_meta = _azure_resource_meta[pulumi_resource.package][pulumi_resource.namespace][
        "resources"
    ][pulumi_resource.resource_class]
    resource_meta["pulumi_resource"] = pulumi_resource

    return AzureResourceMetadata.model_validate(obj=resource_meta)


def get_sub_resource_type(obj: object) -> str | None:
    """
    Return the sub resource name for a given Pulumi resource object
    """
    opts: AzureResourceMetadata = resource_meta(obj=obj)
    return opts.sub_resource_name


def require_sub_resource_type(obj: object) -> str:
    """
    Return the sub resource name for a given Pulumi resource object
    """
    sub_resource_type = get_sub_resource_type(obj=obj)
    if not sub_resource_type:
        raise ValueError(f"Sub Resource Name missing for: {obj}")
    return sub_resource_type


def get_public_dns_zone_name(obj: object) -> DomainName | None:
    """
    Return the public DNS zone name for a given Pulumi resource object
    """
    opts: AzureResourceMetadata = resource_meta(obj=obj)
    return opts.public_dns_zone


def get_private_dns_zone_name(obj: object) -> DomainName | None:
    """
    Return the private DNS zone name for a given Pulumi resource object
    """
    opts: AzureResourceMetadata = resource_meta(obj=obj)
    return opts.private_dns_zone


def require_private_dns_zone_name(obj: object) -> DomainName:
    """
    Return the private DNS zone name for a given Pulumi resource object
    """
    private_dns_zone_name = get_private_dns_zone_name(obj=obj)
    if not private_dns_zone_name:
        raise ValueError(f"Private DNS Zone Name missing for: {obj}")
    return private_dns_zone_name

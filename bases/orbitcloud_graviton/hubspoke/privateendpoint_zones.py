from pulumi_azure_native import (
    appconfiguration,
    containerregistry,
    eventgrid,
    eventhub,
    keyvault,
    search,
    storage,
    web,
)

from orbitcloud_graviton.az_lib.meta import require_private_dns_zone_name
from orbitcloud_graviton.pulumi_lib.types import DomainName


def default_private_endpoint_zones() -> list[DomainName]:
    """
    Return default commonly used private link zones for the hub-spoke architecture.
    Feel free to add more zones as needed as these are cheap to create.

    Returns:
        list[tuple[str, DomainName]]: _description_
    """
    default_privatelink_zones: list[DomainName] = [
        require_private_dns_zone_name(obj=resource)
        for resource in [
            storage.BlobContainer,
            storage.Table,
            storage.Queue,
            keyvault.Vault,
            containerregistry.Registry,
            appconfiguration.ConfigurationStore,
            eventhub.Namespace,
            eventgrid.Domain,
            web.WebApp,
            search.Service,
        ]
    ]
    return default_privatelink_zones

import pulumi
from pulumi_azure_native import keyvault

from orbitcloud_graviton.pulumi_mocks import set_mocks

set_mocks()

from orbitcloud_graviton.az_keyvault import KeyVault, KeyVaultConfig  # noqa
from orbitcloud_graviton.pulumi_lib import AzureStack  # noqa


@pulumi.runtime.test
def test_key_vault(stack: AzureStack):
    config = KeyVaultConfig(public_network_access=keyvault.PublicNetworkAccess.ENABLED)
    kv = KeyVault(stack, config).vault
    assert isinstance(kv, keyvault.Vault)

    def check_parameters(args):
        vault_public_network_access, enable_rbac_authorization = args

        assert vault_public_network_access == keyvault.PublicNetworkAccess.ENABLED
        assert enable_rbac_authorization

    pulumi.Output.all(
        kv.properties.public_network_access,
        kv.properties.enable_rbac_authorization,
    ).apply(check_parameters)

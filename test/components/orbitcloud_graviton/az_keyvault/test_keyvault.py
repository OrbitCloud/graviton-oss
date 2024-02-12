import pulumi
from pulumi_azure_native import keyvault

from orbitcloud_graviton.pulumi_mocks import set_mocks

set_mocks()

from orbitcloud_graviton.az_keyvault import KeyVaultConfig, key_vault  # noqa
from orbitcloud_graviton.pulumi_lib import AzureBase  # noqa


@pulumi.runtime.test
def test_key_vault(stack: AzureBase):
    config = KeyVaultConfig(public_network_access=keyvault.PublicNetworkAccess.ENABLED)
    vault = key_vault(stack, config)
    assert isinstance(vault, keyvault.Vault)

    def check_parameters(args):
        vault_public_network_access, enable_rbac_authorization = args

        assert vault_public_network_access == keyvault.PublicNetworkAccess.ENABLED
        assert enable_rbac_authorization

    pulumi.Output.all(
        vault.properties.public_network_access,
        vault.properties.enable_rbac_authorization,
    ).apply(check_parameters)

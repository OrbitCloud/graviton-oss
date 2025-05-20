from typing import Annotated, Literal

from pulumi_azure_native_app_v20241002preview import app
from pydantic import BaseModel, ConfigDict, Field, FilePath

from orbitcloud_graviton.az_lib.types import StrRef


class SecretBase(BaseModel):
    """Base class for all secret types with common fields and methods."""

    key: str
    filename: str | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class KeyVaultSecret(SecretBase):
    source: Literal["keyvault"] = "keyvault"
    key_vault_url: StrRef | str

    def args(self) -> app.SecretArgs:
        return app.SecretArgs(
            name=self.key,
            identity="System",
            key_vault_url=self.key_vault_url,
        )


class InlineSecret(SecretBase):
    source: Literal["inline"] = "inline"
    value: StrRef | str

    def args(self) -> app.SecretArgs:
        return app.SecretArgs(
            name=self.key,
            value=self.value,
        )


class FileSecret(SecretBase):
    source: Literal["file"] = "file"
    template: FilePath

    def args(self) -> app.SecretArgs:
        with open(self.template) as f:
            content = f.read().strip()
        return app.SecretArgs(
            name=self.key,
            value=content,
        )


Secret = Annotated[KeyVaultSecret | InlineSecret | FileSecret, Field(discriminator="source")]

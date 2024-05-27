from typing import Optional

from pydantic import BaseModel, ConfigDict


class TableRoles(BaseModel):
    reader: Optional[bool] = False
    contributor: Optional[bool] = False

    def roles(self) -> list[str]:
        roles: list[str] = []
        prefix = "Storage Table Data"
        if self.contributor:
            roles.append(f"{prefix} Contributor")
        if self.reader and not self.contributor:
            roles.append(f"{prefix} Reader")
        return roles

    model_config = ConfigDict(extra="forbid")


class BlobRoles(BaseModel):
    reader: Optional[bool] = False
    contributor: Optional[bool] = False
    owner: Optional[bool] = False

    def roles(self) -> list[str]:
        roles: list[str] = []
        prefix = "Storage Blob Data"
        if self.owner:
            roles.append(f"{prefix} Owner")
        if self.contributor and not self.owner:
            roles.append(f"{prefix} Contributor")
        if self.reader and not self.contributor:
            roles.append(f"{prefix} Reader")
        return roles

    model_config = ConfigDict(extra="forbid")


class QueueRoles(BaseModel):
    message_processor: Optional[bool] = False
    message_sender: Optional[bool] = False
    contributor: Optional[bool] = False
    reader: Optional[bool] = False

    def roles(self) -> list[str]:
        roles: list[str] = []
        prefix = "Storage Queue Data"
        if self.message_processor:
            roles.append(f"{prefix} Message Processor")
        if self.message_sender:
            roles.append(f"{prefix} Message Sender")
        if self.contributor:
            roles.append(f"{prefix} Contributor")
        if self.reader and not self.contributor:
            roles.append(f"{prefix} Reader")
        return roles

    model_config = ConfigDict(extra="forbid")


class StorageAccountAppPermissions(BaseModel):
    tables: Optional[TableRoles] = None
    queues: Optional[QueueRoles] = None
    blobs: Optional[BlobRoles] = None

    def roles(self) -> list[str]:
        roles: list[str] = []
        if self.tables:
            roles.extend(self.tables.roles())
        if self.queues:
            roles.extend(self.queues.roles())
        if self.blobs:
            roles.extend(self.blobs.roles())
        return roles

    model_config = ConfigDict(extra="forbid")

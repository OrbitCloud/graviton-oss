from pydantic import BaseModel, ConfigDict


class TableRoles(BaseModel):
    reader: bool | None = False
    contributor: bool | None = False

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
    reader: bool | None = False
    contributor: bool | None = False
    owner: bool | None = False

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
    message_processor: bool | None = False
    message_sender: bool | None = False
    contributor: bool | None = False
    reader: bool | None = False

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
    tables: TableRoles | None = None
    queues: QueueRoles | None = None
    blobs: BlobRoles | None = None

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

import datetime
from typing import Optional, TYPE_CHECKING
import uuid as uuid_pkg
from sqlmodel import Field, SQLModel, Session, select, Relationship
from enum import StrEnum

if TYPE_CHECKING:
    from .item import Item
    from .user import User


class DownloadStatusEnum(StrEnum):
    QUEUED = "0"
    PROCESSING = "1"
    DONE = "2"
    ERROR_UNKNOWN = "3"
    ERROR_TOO_LONG = "4"
    ERROR_DOWNLOAD = "5"
    ERROR_NOT_FOUND = "6"


class DownloadTask(SQLModel, table=True):
    id: uuid_pkg.UUID = Field(
        primary_key=True,
        index=True,
        nullable=False,
        default_factory=uuid_pkg.uuid4,
        exclude=True,
    )
    created_by_id: uuid_pkg.UUID = Field(foreign_key="user.id")
    created_by: "User" = Relationship(back_populates="created_tasks")

    created_at: datetime.datetime = Field(
        nullable=False, default_factory=datetime.datetime.now
    )
    url: str = Field()
    state: DownloadStatusEnum = Field(default=DownloadStatusEnum.QUEUED)
    downloaded_bytes: Optional[int] = Field()

    item_id: Optional[uuid_pkg.UUID] = Field(foreign_key="item.id")
    item: Optional["Item"] = Relationship(back_populates="tasks")

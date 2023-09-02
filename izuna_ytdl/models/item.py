import datetime
from typing import List, TYPE_CHECKING
import uuid as uuid_pkg
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from .download_task import DownloadTask


class Item(SQLModel, table=True):
    id: uuid_pkg.UUID = Field(
        primary_key=True,
        index=True,
        nullable=False,
        default_factory=uuid_pkg.uuid4,
        exclude=True,
    )

    video_id: str = Field(unique=True, nullable=False, index=True)
    created_by_username: str = Field(nullable=False)
    created_at: datetime.datetime = Field(
        nullable=False, default_factory=datetime.datetime.now
    )
    original_url: str = Field(nullable=False)
    original_query: str = Field(nullable=False)
    remote_key: str = Field(nullable=False)
    total_bytes: int | None

    tasks: List["DownloadTask"] = Relationship(back_populates="item")

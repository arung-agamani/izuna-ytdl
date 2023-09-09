import datetime
from typing import List, TYPE_CHECKING
import uuid as uuid_pkg
from sqlmodel import Field, SQLModel, Relationship, Session

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

    name: str = Field(nullable=False)
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

    def save(self, session: Session):
        session.add(self)
        session.commit()
        session.refresh(self)

    def set_total_bytes(self, session: Session, bytes: int):
        self.total_bytes = bytes
        self.save(session)

    def set(self, session: Session, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.save(session)

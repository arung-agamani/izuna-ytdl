import datetime
from typing import Optional
import uuid as uuid_pkg

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: uuid_pkg.UUID = Field(
        primary_key=True, index=True, nullable=False, default_factory=uuid_pkg.uuid4
    )
    username: str = Field(unique=True, nullable=False, index=True)
    password: str = Field(nullable=False)
    created_at: datetime.datetime = Field(
        nullable=False, default_factory=datetime.datetime.now
    )

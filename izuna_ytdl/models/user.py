import datetime
from typing import Optional
import uuid as uuid_pkg
from sqlmodel import Field, SQLModel, Session, select

from izuna_ytdl.auth import hash_password, verify_password


class User(SQLModel, table=True):
    id: uuid_pkg.UUID = Field(
        primary_key=True,
        index=True,
        nullable=False,
        default_factory=uuid_pkg.uuid4,
        exclude=True,
    )
    username: str = Field(unique=True, nullable=False, index=True)
    password_hash: str = Field(nullable=False, exclude=True)
    created_at: datetime.datetime = Field(
        nullable=False, default_factory=datetime.datetime.now
    )

    @staticmethod
    def create(session: Session, *, username: str, password_plain: str):
        session.begin()
        u = User(username=username)
        u.set_password(password_plain)
        session.add(u)
        session.commit()

    @staticmethod
    def get_by_username(session: Session, username: str):
        stmt = select(User).where(User.username == username)
        result = session.exec(stmt)
        user = result.first()
        return user

    def is_password_match(self, password: str) -> bool:
        return verify_password(self.password_hash, password)

    def set_password(self, password_plain: str):
        p = hash_password(password_plain)
        self.password_hash = p

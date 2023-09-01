import datetime
from typing import Optional
import uuid as uuid_pkg
from sqlmodel import Field, SQLModel, Session, select

from izuna_ytdl.database import engine


class User(SQLModel, table=True):
    id: uuid_pkg.UUID = Field(
        primary_key=True, index=True, nullable=False, default_factory=uuid_pkg.uuid4
    )
    username: str = Field(unique=True, nullable=False, index=True)
    password: str = Field(nullable=False)
    created_at: datetime.datetime = Field(
        nullable=False, default_factory=datetime.datetime.now
    )

    @staticmethod
    def create(*, username: str, password: str):
        with Session(engine) as session:
            u = User(username=username, password=password)
            session.add(u)
            session.commit()
            return u

    @staticmethod
    def get_by_username(username: str):
        with Session(engine) as session:
            stmt = select(User).where(User.username == username)
            result = session.exec(stmt)
            user = result.first()
            return user

    def is_password_match(self, password: str) -> bool:
        # TODO: implement password hashing
        return self.password == password

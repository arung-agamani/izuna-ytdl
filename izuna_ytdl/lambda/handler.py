import boto3
import yt_dlp
import os
import datetime
import logging
from typing import Optional, TYPE_CHECKING, List
import uuid as uuid_pkg
from uuid import UUID
from sqlmodel import Field, SQLModel, Session, select, Relationship, create_engine
from enum import StrEnum

engine = create_engine(
    os.environ["DB_CONNECTION_URL"],
    # echo=True,
)
s3 = boto3.client("s3")


def get_session():
    with Session(engine) as session:
        yield session


class DownloadStatusEnum(StrEnum):
    QUEUED = "0"
    PROCESSING = "1"
    DONE = "2"
    ERROR_UNKNOWN = "3"
    ERROR_TOO_LONG = "4"
    ERROR_DOWNLOAD = "5"
    ERROR_NOT_FOUND = "6"


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

    @staticmethod
    def get_by_video_id(session: Session, video_id: str):
        stmt = select(Item).where(Item.video_id == video_id)
        result = session.exec(stmt)
        item = result.first()
        return item

    def set(self, session: Session, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.save(session)


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

    created_tasks: List["DownloadTask"] = Relationship(back_populates="created_by")

    @staticmethod
    def create(session: Session, *, username: str, password_plain: str):
        u = User(username=username)
        u.set_password(password_plain)
        session.add(u)
        session.commit()
        return u

    @staticmethod
    def get_by_username(session: Session, username: str):
        stmt = select(User).where(User.username == username)
        result = session.exec(stmt)
        user = result.first()
        return user


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
    title: str = Field()
    state: DownloadStatusEnum = Field(default=DownloadStatusEnum.QUEUED)
    downloaded_bytes: Optional[int] = Field()

    item_id: Optional[uuid_pkg.UUID] = Field(foreign_key="item.id")
    item: Optional["Item"] = Relationship(back_populates="tasks")

    @staticmethod
    def get(session: Session, id: UUID):
        res = session.exec(select(DownloadTask).where(DownloadTask.id == id))
        return res.first()

    def save(self, session: Session):
        session.add(self)
        session.commit()
        session.refresh(self)

    def set_state(self, session: Session, state: DownloadStatusEnum):
        self.state = state
        self.save(session)

    def set_downloaded_bytes(self, session: Session, bytes: int):
        self.downloaded_bytes = bytes
        self.save(session)

    def set(self, session: Session, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        logging.debug("===========================Before save")
        self.save(session)
        logging.debug("===========================After save")


def download(session: Session, id: str, task: DownloadTask, s3):
    final_filename = None
    final_filepath = ""

    def yt_dlp_monitor(d):
        nonlocal final_filename
        nonlocal final_filepath
        if d.get("status") == "finished":
            final_filename = d.get("info_dict").get("filepath")
            final_filepath = (
                d.get("info_dict").get("__files_to_move").get(final_filename)
            )

    def progress_hook(d: dict):
        task.set_downloaded_bytes(session, d["downloaded_bytes"])
        task.item.set_total_bytes(session, d["total_bytes"])

    try:
        ydl_opts = {
            "extract_flat": "discard_in_playlist",
            "final_ext": "mp3",
            "format": "ba",
            "fragment_retries": 10,
            "ffmpeg_location": "/opt/bin/ffmpeg",
            "ignoreerrors": "only_download",
            "outtmpl": {"default": "/tmp/ytdlp/%(title)s.%(ext)s"},
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "nopostoverwrites": False,
                    "preferredcodec": "mp3",
                    "preferredquality": "5",
                },
                {"key": "FFmpegConcat", "only_multi_video": True, "when": "playlist"},
            ],
            "retries": 10,
            "postprocessor_hooks": [yt_dlp_monitor],
            "progress_hooks": [progress_hook],
        }
        logging.debug("===========================Before task set session")
        task.set(session, state=DownloadStatusEnum.PROCESSING)
        logging.debug("===========================After task set session")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(
                f"https://www.youtube.com/watch?v={id}", download=False
            )
            duration = info.get("duration")
            if duration > 600:
                task.set(session, state=DownloadStatusEnum.ERROR_TOO_LONG)
                raise Exception("duration too long")

            task.set(session, title=info.get("title"))
            ydl.download(f"https://www.youtube.com/watch?v={id}")

            # os.remove(final_filepath)
            # raise Exception("stop")

            logging.debug("Download complete")
            logging.debug(f"End filename: ${final_filename}")
            logging.debug(f"End filepath: ${final_filepath}")
            remote_key = f"public/{id}/{final_filename}"
            task.item.set(
                session,
                name=final_filename,
                remote_key=remote_key,
            )
            s3.upload_file(final_filepath, os.environ["YTDL_BUCKET_NAME"], remote_key)
            task.set(
                session,
                title=final_filename,
                state=DownloadStatusEnum.DONE,
            )
            os.remove(final_filepath)
            return

    except yt_dlp.utils.DownloadError as err:
        logging.error("Download error")
        logging.error(err)
        if err.msg.rfind("Video unavailable") != -1:
            task.set(session, state=DownloadStatusEnum.ERROR_NOT_FOUND)
        else:
            task.set(session, state=DownloadStatusEnum.ERROR_DOWNLOAD)
    except Exception as err:
        errm = f"Other errors: {err.__class__.__name__} {err}"
        logging.error(errm)
        task.set(session, state=DownloadStatusEnum.ERROR_UNKNOWN)
        task.set_downloaded_bytes(session, 0)


def handler(event, context):
    id = event["id"]
    task_data = event["task"]
    item_data = event["item"]
    user_data = event["user"]
    session = Session(engine)
    logging.debug("===========================Before item")
    # item = Item.parse_obj(item_data)
    user = User.get_by_username(session, user_data["username"])
    logging.debug("===========================After user")
    item = Item.get_by_video_id(session, item_data["video_id"])
    if item is None:
        item = Item(
            created_by_username=user.username,
            name="",
            original_query=item_data["original_query"],
            original_url=item_data["original_url"],
            remote_key="",
            video_id=id,
        )
    logging.debug("===========================After item")
    task = DownloadTask(
        created_by=user,
        created_by_id=user.id,
        url=task_data["url"],
        title=task_data["title"],
        state=task_data["state"],
        downloaded_bytes=task_data["downloaded_bytes"],
        item=item,
        item_id=item.id,
    )
    logging.debug("===========================After task")

    import pprint

    # pprint.pprint(task)
    # pprint.pprint(item)
    # pprint.pprint(user)
    try:
        download(session, id, task, s3)
        print("Done")
        return {"statusCode": 200}

    except Exception as e:
        # print(e)
        return {"statusCode": 500}
    finally:
        session.close()


event_str = """{
  "id": "OIBODIPC_8Y",
  "user": {
    "username": "test",
    "password_hash": "asdfadsfasdfadsfasdfasdf"
  },
  "item": {
    "name": "",
    "video_id": "OIBODIPC_8Y",
    "created_by_username": "test",
    "original_query": "https://www.youtube.com/watch?v=OIBODIPC_8Y",
    "original_url": "https://www.youtube.com/watch?v=OIBODIPC_8Y",
    "remote_key": ""
  },
  "task": {
    "url": "https://www.youtube.com/watch?v=OIBODIPC_8Y",
    "title": "",
    "state": "0",
    "created_by": {
      "username": "test",
      "password_hash": "asdfadsfasdfadsfasdfasdf"
    },
    "downloaded_bytes": null
  }
}"""

if __name__ == "__main__":
    import json

    event = json.loads(event_str)
    handler(event, {})

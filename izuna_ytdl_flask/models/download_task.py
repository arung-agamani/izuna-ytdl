import datetime
from enum import Enum
import logging
from redis_om import JsonModel, Field, NotFoundError
from typing import cast, Optional
from .user import get_user
from .item import Item, create_item


class DownloadStatusEnum(Enum):
    QUEUED = "0"
    PROCESSING = "1"
    DONE = "2"
    ERROR_UNKNOWN = "3"
    ERROR_TOO_LONG = "4"
    ERROR_DOWNLOAD = "5"
    ERROR_NOT_FOUND = "6"


class DownloadTask(JsonModel):
    title: str
    id: str = Field(index=True)
    created_by: str = Field(index=True)
    created_at: datetime.datetime = Field(index=True)
    url: str
    state: DownloadStatusEnum
    item: Optional[Item]
    downloaded_bytes: Optional[int]

    def update_state(self, state: DownloadStatusEnum):
        self.state = state
        self.save()

    def update_title(self, title: str):
        self.title = title
        self.save()

    def set_item(self, item: Item):
        self.item = item
        self.save()

    def update(self, title: str, state: DownloadStatusEnum):
        self.title = title
        self.state = state
        self.save()

    def set_downloaded_bytes(self, v: int):
        self.downloaded_bytes = v
        self.save()


def get_task(id: str):
    try:
        task = DownloadTask.find(DownloadTask.id == id).first()
        task = cast(DownloadTask, task)
        return task
    except NotFoundError as e:
        print(e)
        return None


def get_task_with_user(id: str, username: str):
    try:
        task = DownloadTask.find(
            (DownloadTask.id == id) & (DownloadTask.created_by == username)
        ).first()
        task = cast(DownloadTask, task)
        return task
    except NotFoundError as e:
        logging.error(e)
        return None


def get_task_by_user(username: str):
    try:
        user = get_user(username)
        if user is None:
            return []
        tasks = DownloadTask.find(DownloadTask.created_by == user.username).all()
        tasks.sort(key=lambda task: task.created_at)
        return tasks
    except NotFoundError as e:
        print(e)
        return []


def create_task(id: str, url: str, title: str, created_by: str):
    task = get_task_with_user(id, created_by)
    if task is not None:
        return None
    now = datetime.datetime.now()
    item = create_item(id, "", created_by, now, url, url, "")
    task = DownloadTask(
        id=id,
        title=title,
        url=url,
        state=DownloadStatusEnum.QUEUED,
        created_by=created_by,
        created_at=now,
        item=item,
    )
    task.save()
    # task.set_item(item)
    return task


def create_task_with_item(id: str, url: str, title: str, created_by: str, item: Item):
    task = get_task_with_user(id, created_by)
    if task is not None:
        return None
    now = datetime.datetime.now()
    task = DownloadTask(
        id=id,
        title=title,
        url=url,
        state=DownloadStatusEnum.QUEUED,
        created_by=created_by,
        created_at=now,
        item=item,
    )
    task.save()
    # task.set_item(item)
    return task


def create_task_without_item(id: str, url: str, title: str, created_by: str):
    task = get_task_with_user(id, created_by)
    if task is not None:
        return None
    now = datetime.datetime.now()
    task = DownloadTask(
        id=id,
        title=title,
        url=url,
        state=DownloadStatusEnum.QUEUED,
        created_by=created_by,
        created_at=now,
    )
    task.save()
    return task

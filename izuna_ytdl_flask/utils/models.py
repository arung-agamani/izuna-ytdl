from redis import Redis
from dataclasses import dataclass
from datetime import datetime
from pydantic import BaseModel, ValidationError
from enum import Enum
import json
from uuid import uuid4
from typing import cast
from .redis import get_connection


class DownloadStatus(Enum):
    QUEUED = "0"
    DOWNLOADING = "1"
    DOWNLOADED = "2"
    DELETED = "3"
    ERRORED = "4"

    def __str__(self):
        return self.value


@dataclass
class DownloadInfo:
    id: str
    status: DownloadStatus
    message: str


class User(BaseModel):
    id: str
    username: str
    password: str
    date_created: datetime


def create_user(username: str, password: str):
    id = str(uuid4())
    date_created = datetime.now()
    user = User(id=id, username=username, password=password, date_created=date_created)
    payload = user.model_dump_json()
    # check if user exists
    r = cast(Redis, get_connection())
    if r.get(f"user:{username}") is not None:
        return False
    r.set(f"user:{username}", payload)
    return user


def get_user(username: str, password: str):
    r = cast(Redis, get_connection())
    user_raw = r.get(f"user:{username}")
    if user_raw is None:
        return 0
    user_obj = json.loads(user_raw)
    user = User(**user_obj)
    if user.password != password:
        return -1
    return user


def get_user_only(username: str):
    r = cast(Redis, get_connection())
    user_raw = r.get(f"user:{username}")
    if user_raw is None:
        return 0
    user_obj = json.loads(user_raw)
    user = User(**user_obj)
    return user


def del_user(username: str):
    r = cast(Redis, get_connection())
    user_raw = r.get(f"user:{username}")
    if user_raw is None:
        return False
    r.delete(f"user:{username}")
    return True


def get_download_info(id: str, r: Redis):
    status = r.get(f"status:{id}")
    message = r.get(f"message:{id}")
    # print("GET DOWNLOAD INFO DEBUG")
    # print(status)
    # print(message)
    # print("END DEBUG")
    if None in [status, message]:
        return None
    if "null" in [status, message]:
        return None
    return DownloadInfo(id, status, message)


def set_download_info(info: DownloadInfo, r: Redis):
    p = r.pipeline()
    p.set(f"status:{info.id}", json.dumps(info.status, default=str))
    p.set(f"message:{info.id}", info.message)
    res = p.execute()
    if None in res:
        return None
    print(res)
    return res


def set_download_status(id: str, status: DownloadStatus, r: Redis):
    if r.set(f"status:{id}", json.dumps(status, default=str)) is None:
        return False
    return True


def del_download_info(id: str, r: Redis):
    p = r.pipeline()
    p.delete(f"status:{id}", f"message:{id}")
    res = p.execute()
    if 0 in res:
        return False
    return True

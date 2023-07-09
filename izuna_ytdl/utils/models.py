from redis import Redis
from dataclasses import dataclass
from enum import Enum
import json


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
    p.set(f"status:{info.id}", json.dumps(
        info.status, default=str))
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

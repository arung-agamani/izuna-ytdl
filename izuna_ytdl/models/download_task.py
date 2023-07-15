import datetime
from redis_om import JsonModel, Field, NotFoundError
from typing import cast


QUEUED = "0"
PROCESSING = "1"
DONE = "2"
ERROR_UNKNOWN = "3"
ERROR_TOO_LONG = "4"


class DownloadTask(JsonModel):
    title: str
    id: str = Field(index=True)
    created_by: str = Field(index=True)
    url: str
    state: str

    def update_state(self, state: str):
        self.state = state
        self.save()

    def update_title(self, title: str):
        self.title = title
        self.save()

    def update(self, title: str, state: str):
        self.title = title
        self.state = state
        self.save()


def get_task(id: str):
    try:
        task = DownloadTask.find(
            DownloadTask.id == id
        ).first()
        task = cast(DownloadTask, task)
        return task
    except NotFoundError as e:
        print(e)
        return None


def create_task(id: str, url: str, title: str, created_by: str):
    task = get_task(id)
    if task is not None:
        return None
    task = DownloadTask(
        id=id, title=title, url=url, state=QUEUED, created_by=created_by
    )
    task.save()
    return task

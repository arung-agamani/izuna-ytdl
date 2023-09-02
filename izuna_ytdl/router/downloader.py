from typing import Annotated, Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from pydantic import BaseModel

from izuna_ytdl.models import User, DownloadTask, Item
from izuna_ytdl.database import get_session
from izuna_ytdl import auth

router = APIRouter()


class DownloadTaskOut(BaseModel):
    id: UUID
    url: str
    state: str
    downloaded_bytes: Optional[int]
    total_bytes: Optional[int]
    title: Optional[str]


@router.get("/tasks")
async def get_tasks(
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(auth.get_login_user)],
):
    tasks = session.exec(
        select(DownloadTask, Item)
        .join(Item, isouter=True)
        .where(DownloadTask.created_by == user)
    )

    results: List[DownloadTaskOut] = []
    for task, item in tasks:
        out = DownloadTaskOut(
            id=task.id,
            url=task.url,
            downloaded_bytes=task.downloaded_bytes,
            state=task.state,
            title=task.title,
        )
        if item != None:
            out.total_bytes = item.total_bytes
        results.append(out)

    return results

from typing import Annotated, Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import PlainTextResponse
from sqlmodel import Session, select
from pydantic import BaseModel
import boto3
from botocore.exceptions import ClientError

from izuna_ytdl.models import User, DownloadTask, Item
from izuna_ytdl.database import get_session
from izuna_ytdl import auth, config

router = APIRouter()
s3 = boto3.client("s3")


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
        if item is not None:
            out.total_bytes = item.total_bytes
        results.append(out)

    return results


@router.get("/retrieve", response_model=str)
async def get_download_link(
    session: Annotated[Session, Depends(get_session)],
    id: str,
) -> str:
    task = DownloadTask.get(session, id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="task not found"
        )

    try:
        res = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": config.BUCKET_NAME, "Key": task.item.remote_key},
            ExpiresIn=600,
        )
        return PlainTextResponse(content=res, status_code=status.HTTP_201_CREATED)
    except ClientError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="s3 url generate error",
        )

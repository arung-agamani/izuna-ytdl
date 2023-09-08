import os
from typing import Annotated, Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, status, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlmodel import Session, select
import sqlalchemy as sa
from pydantic import BaseModel, HttpUrl, validator, parse_obj_as
import boto3
from botocore.exceptions import ClientError
from urllib.parse import parse_qs
import logging

import yt_dlp

from izuna_ytdl.models import User, DownloadTask, Item
from izuna_ytdl.database import get_session
from izuna_ytdl import auth, config
from izuna_ytdl.models.download_task import DownloadStatusEnum

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
    user: Annotated[User, Depends(auth.get_login_user)],
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


class DownloadIn(BaseModel):
    url: HttpUrl

    @validator("url")
    def validate_url_host(cls, v: HttpUrl):
        if v.host not in [
            "www.youtube.com",
            "youtube.com",
            "youtu.be",
            "music.youtube.com",
        ]:
            raise ValueError("invalid host")
        if v.host == "youtu.be":
            path = v.path.split("/")
            if len(path) < 2:
                raise ValueError("invalid youtu.be link")
            video_id = path[1]
            print(video_id)
            v = parse_obj_as(HttpUrl, f"http://youtube.com/watch?v={video_id}")
        return v

    @validator("url")
    def validate_youtube_url(cls, v: HttpUrl):
        if v.path != "/watch":
            raise ValueError("invalid url")

        query = parse_qs(v.query)
        if "v" not in query:
            raise ValueError("missing v (?v=something)")
        if len(query["v"]) > 1:
            raise ValueError("multiple v params")
        return v

    def get_video_id(self):
        query = parse_qs(self.url.query)
        return query["v"][0]


@router.post("/download")
async def post_download(
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(auth.get_login_user)],
    background_tasks: BackgroundTasks,
    params: DownloadIn,
):
    stmt = (
        sa.select(sa.func.count())
        .select_from(DownloadTask)
        .where(DownloadTask.created_by == user)
    )
    task_count = session.scalar(stmt)
    if task_count > config.MAX_USER_TASK:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Task exceeded limit of {config.MAX_USER_TASK}",
        )

    video_id = params.get_video_id()

    [task, item] = session.exec(
        select(DownloadTask, Item)
        .join(Item, isouter=True)
        .where((Item.video_id == video_id) & (DownloadTask.created_by == user))
    ).first()

    if task is None:
        if item is not None:
            logging.debug(
                f"No task found for {user.username}"
                f"but item with vid id {item.video_id} exists"
                ". Associating..."
            )
            newTask = DownloadTask(
                created_by=user,
                title=item.name,
                item=item,
                url=params.url,
                state=DownloadStatusEnum.DONE,
            )
            session.add(newTask)
            session.commit()
            return JSONResponse(
                {
                    "success": True,
                    "message": "Item exists for queried item."
                    "Associated user's data to the item",
                },
                status_code=status.HTTP_201_CREATED,
            )
        logging.debug("No task found. Creating and queueing")
        newItem = Item(
            created_by_username=user.username,
            name="",
            original_query=params.url,
            original_url=params.url,
            remote_key="",
            video_id=video_id,
        )
        newItem.save(session)
        newTask = DownloadTask(
            item=newItem,
            title="",
            url=params.url,
            created_by=user,
        )
        newTask.save(session)
        background_tasks.add_task(download, video_id, newTask)
    else:
        logging.debug("Existing task found. Checking")
        if task.state == DownloadStatusEnum.QUEUED:
            logging.debug("Existing task found and queued. Executing")
            background_tasks.add_task(download, video_id, task)
        elif task.state == DownloadStatusEnum.DONE:
            return JSONResponse(
                {
                    "success": True,
                    "message": "Item have been downloaded",
                },
                status_code=status.HTTP_200_OK,
            )
        else:
            logging.debug(f"Existing task state is {task.state}")
            task.set_state(DownloadStatusEnum.QUEUED)
            background_tasks.add_task(download, video_id, task)

    return JSONResponse(
        {"success": True, "message": f"Queueing download task for Youtube {video_id}"},
        status_code=status.HTTP_201_CREATED,
    )


def download(
    session: Annotated[Session, Depends(get_session)], id: str, task: DownloadTask
):
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
            "ignoreerrors": "only_download",
            "outtmpl": {"default": "%(title)s.%(ext)s"},
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
        task.set(session, state=DownloadStatusEnum.PROCESSING)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(
                f"https://www.youtube.com/watch?v={id}", download=False
            )
            duration = info.get("duration")
            if duration > 600:
                task.set(session, state=DownloadStatusEnum.ERROR_TOO_LONG)
                return

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
            s3.upload_file(final_filepath, config.BUCKET_NAME, remote_key)
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
        logging.error(f"Other errors: {err.__class__.__name__}")
        task.set(session, state=DownloadStatusEnum.ERROR_UNKNOWN)
        task.set_downloaded_bytes(0)

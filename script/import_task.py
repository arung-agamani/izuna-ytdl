from sqlmodel import create_engine, SQLModel, Session, select

from izuna_ytdl import config
from izuna_ytdl.models import User, Item, DownloadTask
from izuna_ytdl_flask.models.item import Item as RedisItem
from izuna_ytdl_flask.models.download_task import DownloadTask as RedisTask


engine = create_engine(config.DB_CONNECTION_URL, echo=True)

with Session(engine) as session:
    for task in RedisTask.find():
        task: RedisTask = task
        newTask = DownloadTask(
            created_by=session.exec(
                select(User).where(User.username == task.created_by).limit(1)
            ).one(),
            created_at=task.created_at,
            downloaded_bytes=task.downloaded_bytes,
            state=task.state,
            url=task.url,
            item=session.exec(select(Item).where(Item.video_id == task.id)).one(),
        )
        session.add(newTask)
    session.commit()

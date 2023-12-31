from sqlmodel import create_engine, Session

from izuna_ytdl import config
from izuna_ytdl.models import Item
from izuna_ytdl_flask.models.item import Item as RedisItem


engine = create_engine(config.DB_CONNECTION_URL, echo=True)

with Session(engine) as session:
    for item in RedisItem.find():
        item: RedisItem = item
        newItem = Item(
            video_id=item.id,
            created_by_username=item.created_by,
            created_at=item.created_at,
            original_url=item.original_url,
            original_query=item.original_query,
            remote_key=item.remote_key,
            total_bytes=item.total_bytes,
            name=item.name,
        )
        session.add(newItem)
    session.commit()

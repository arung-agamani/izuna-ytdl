import datetime
from redis_om import JsonModel, Field, NotFoundError
from typing import Optional, cast
import logging


class Item(JsonModel):
    id: str = Field(index=True)
    name: str
    created_by: str = Field(index=True)
    created_at: datetime.datetime = Field(index=True)
    original_url: str
    original_query: str
    remote_key: str
    total_bytes: Optional[int]

    class Meta:
        model_key_prefix = "izuna_ytdl.models.item.Item"

    def set_remote_key(self, key: str):
        self.remote_key = key
        self.save()

    def set_name(self, name: str):
        self.name = name
        self.save()

    def set_total_bytes(self, v: int):
        self.total_bytes = v
        self.save()


def get_item(id: str):
    try:
        item = Item.find(Item.id == id).first()
        item = cast(Item, item)
        return item
    except NotFoundError as e:
        logging.error(e)
        return None


def create_item(
    id: str,
    name: str,
    created_by: str,
    created_at: datetime.datetime,
    original_url: str,
    original_query: str,
    remote_key: str = "",
):
    item = get_item(id)
    if item is not None:
        return None
    item = Item(
        id=id,
        name=name,
        created_by=created_by,
        created_at=created_at,
        original_url=original_url,
        original_query=original_query,
        remote_key=remote_key,
    )
    item.save()
    return item

import datetime
from typing import Optional
from pydantic import EmailStr

from redis_om import HashModel, JsonModel, Field, model


class User(JsonModel):
    username: str = Field(index=True)
    password: str
    date_created: datetime.datetime

    class Meta:
        model_key_prefix = "izuna_ytdl.models.user.User"


def create_user(username: str, password: str):
    # check if user exist
    user = get_user(username)
    if user is not None:
        return False
    user = User(
        username=username, password=password, date_created=datetime.datetime.now()
    )

    user.save()
    return user


def get_user(username: str):
    try:
        user = User.find(User.username == username).first()
        return user
    except model.NotFoundError as e:
        print(f"Error happened when querying user '{username}'")
        return None

from sqlmodel import create_engine, SQLModel, Session

from izuna_ytdl.models.user import User
from izuna_ytdl.config import *

from izuna_ytdl_flask.models.user import User as fUser

engine = create_engine(DB_CONNECTION_URL, echo=True)

users = fUser.find()
for u in users:
    u: fUser = u
    User.create(username=u.username, password_plain=u.password)

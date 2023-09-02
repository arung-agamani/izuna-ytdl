from sqlmodel import create_engine, Session

from izuna_ytdl.models.user import User
from izuna_ytdl import config

from izuna_ytdl_flask.models.user import User as fUser

engine = create_engine(config.DB_CONNECTION_URL, echo=True)

with Session(engine) as session:
    users = fUser.find()
    for u in users:
        u: fUser = u
        User.create(session, username=u.username, password_plain=u.password)

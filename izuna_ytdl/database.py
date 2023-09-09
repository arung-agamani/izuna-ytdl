from sqlmodel import Session, create_engine

from izuna_ytdl.config import DB_CONNECTION_URL


engine = create_engine(
    DB_CONNECTION_URL,
    # echo=True,
)


def get_session():
    with Session(engine) as session:
        yield session

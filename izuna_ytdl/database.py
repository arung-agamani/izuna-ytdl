from sqlmodel import create_engine

from izuna_ytdl.config import DB_CONNECTION_URL


engine = create_engine(DB_CONNECTION_URL, echo=True)

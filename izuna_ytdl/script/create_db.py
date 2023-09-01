from sqlmodel import create_engine, SQLModel

from ..models.user import User

# sqlite_file_name = "database.db"
# sqlite_url = f"sqlite:///{sqlite_file_name}"
sqlite_url = "sqlite://"

engine = create_engine(sqlite_url, echo=True)

print("start")

SQLModel.metadata.create_all(engine)

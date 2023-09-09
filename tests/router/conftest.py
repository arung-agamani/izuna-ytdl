import pytest

# from fastapi import Session
from fastapi.testclient import TestClient

from izuna_ytdl.main import app
from izuna_ytdl.models import User, DownloadTask, Item
from izuna_ytdl.database import engine
from izuna_ytdl.auth import get_login_user

from sqlmodel import delete, Session, SQLModel

from izuna_ytdl.models.download_task import DownloadStatusEnum


@pytest.fixture(autouse=True, scope="module")
def test_engine():
    # engine.echo = True
    SQLModel.metadata.create_all(engine)
    yield engine
    with Session(engine) as session:
        session.exec(delete(User))
        session.exec(delete(DownloadTask))
        session.exec(delete(Item))
        session.commit()


@pytest.fixture(scope="module")
def session(test_engine):
    with Session(test_engine) as session:
        yield session


@pytest.fixture(scope="module")
def client(test_engine):
    # def override_use_session():
    #     with Session(test_engine) as session:
    #         yield session

    # app.dependency_overrides[get_session] = override_use_session

    yield TestClient(app)


@pytest.fixture(scope="module")
def register_user(client, test_engine, session):
    resp = client.post(
        "/api/user/register",
        json={
            "username": "test",
            "password": "qwer1234",
            "signin_code": "A" * 32,
        },
    )
    assert resp.status_code == 201
    assert resp.json() == "created"
    yield
    session.exec(delete(User).where(User.username == "test"))
    session.commit()


@pytest.fixture(scope="module")
def login_cookie(client, register_user):
    resp = client.post(
        "/api/user/login",
        json={
            "username": "test",
            "password": "qwer1234",
        },
    )
    assert resp.status_code == 200
    cookie = resp.cookies.get("access_token_cookie")
    assert cookie is not None
    yield cookie


@pytest.fixture(scope="module")
def login_user(test_engine, login_cookie, session):
    yield get_login_user(session, login_cookie)


@pytest.fixture(scope="function")
def stock_items(test_engine, login_user, session):
    url = "https://youtube.com/watch?v=86IxCGKUOzY"
    item1 = Item(
        created_by_username=login_user.username,
        name="生きるよすが",
        original_query=url,
        original_url=url,
        remote_key="public/86IxCGKUOzY/生きるよすが.mp3",
        video_id="86IxCGKUOzY",
    )
    item1.save(session)

    yield [item1]
    session.exec(delete(Item))
    session.commit()


@pytest.fixture(scope="function")
def stock_tasks(test_engine, login_user, stock_items, session):
    res = []
    for item in stock_items:
        newTask = DownloadTask(
            item=item,
            title="生きるよすが",
            url=item.original_url,
            created_by=login_user,
            state=DownloadStatusEnum.QUEUED,
        )
        newTask.save(session)
        res.append(newTask)

    yield res

    session.exec(delete(DownloadTask))
    session.commit()

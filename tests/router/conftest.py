import pytest

# from fastapi import Session
from fastapi.testclient import TestClient

from izuna_ytdl.main import app
from izuna_ytdl.models import User, DownloadTask, Item
from izuna_ytdl.database import engine

from sqlmodel import delete, Session, SQLModel


@pytest.fixture(autouse=True, scope="module")
def test_engine():
    SQLModel.metadata.create_all(engine)
    yield engine
    with Session(engine) as session:
        session.exec(delete(User))
        session.exec(delete(DownloadTask))
        session.exec(delete(Item))
        session.commit()


@pytest.fixture(scope="module")
def client(test_engine):
    # def override_use_session():
    #     with Session(test_engine) as session:
    #         yield session

    # app.dependency_overrides[get_session] = override_use_session

    yield TestClient(app)


@pytest.fixture(scope="module")
def register_user(client, test_engine):
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
    with Session(engine) as session:
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

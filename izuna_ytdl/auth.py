from fastapi import Depends, Response, HTTPException, status, Cookie
from typing import Annotated
from argon2 import PasswordHasher
from sqlmodel import Session

from izuna_ytdl.database import get_session

ph = PasswordHasher()


def hash_password(password: str):
    return ph.hash(password)


def verify_password(password_hash, password):
    return ph.verify(password_hash, password)


def set_access_cookies(resp: Response, username: str):
    resp.set_cookie(key="access_token_cookie", value=username, httponly=True)


def unset_access_cookies(resp: Response):
    resp.set_cookie(key="access_token_cookie", value="", httponly=True)


def get_login_user(
    session: Annotated[Session, Depends(get_session)],
    access_token_cookie: Annotated[str, Cookie()],
):
    from izuna_ytdl.models import User

    if access_token_cookie is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="missing access token"
        )

    username = access_token_cookie
    user = User.get_by_username(session, username=username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="invalid access token"
        )

    return user

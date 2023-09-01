from fastapi import Response, Header, HTTPException, status, Request, Cookie
from typing import Annotated, Optional
from izuna_ytdl.models import User


def set_access_cookies(resp: Response, username: str):
    resp.set_cookie(key="access_token_cookie", value=username, httponly=True)


def unset_access_cookies(resp: Response):
    resp.set_cookie(key="access_token_cookie", value="", httponly=True)


async def get_login_user(
    req: Request,
    access_token_cookie: Annotated[Optional[str], Cookie()] = None,
):
    print(req.headers)
    if access_token_cookie == None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="missing access token"
        )

    username = access_token_cookie
    user = User.get_by_username(username=username)
    if user == None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="invalid access token"
        )

    return user

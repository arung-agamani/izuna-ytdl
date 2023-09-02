from fastapi import APIRouter, Response, status, Depends, Header, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Annotated
from .. import auth, config

from izuna_ytdl.models import User

router = APIRouter()


class Login(BaseModel):
    username: str
    password: str


@router.post("/login")
async def user_login(login: Login):
    user = User.get_by_username(username=login.username)
    if user == None or not user.is_password_match(login.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid login credentials"
        )

    resp = PlainTextResponse("user logged in")
    auth.set_access_cookies(resp, user.username)
    return resp


class UserOut(BaseModel):
    username: str


@router.get("/me")
async def user_me(user: Annotated[User, Depends(auth.get_login_user)]) -> UserOut:
    return user


@router.post("/logout")
async def user_logout(user: Annotated[User, Depends(auth.get_login_user)]):
    resp = PlainTextResponse("user logged out")
    auth.unset_access_cookies(resp)
    return resp


class UserRegister(BaseModel):
    username: str
    password: str
    signin_code: str


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def user_register(register: UserRegister):
    if register.signin_code != config.MASTER_SIGNUP_CODE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid signup code"
        )

    user = User.get_by_username(register.username)
    if user != None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="already registered"
        )

    user = User.create(username=register.username, password_plain=register.password)
    return user

import logging
import os
import base64
import hashlib
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status, Cookie
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated
from argon2 import PasswordHasher
from sqlmodel import Session
from jose import JWTError, jwt

from izuna_ytdl.database import get_session
from izuna_ytdl import config

ALGORITHM = "HS256"

ph = PasswordHasher()


def hash_password(password: str):
    return ph.hash(password)


def verify_password(password_hash, password):
    return ph.verify(password_hash, password)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/user/token")


def get_login_user(
    session: Annotated[Session, Depends(get_session)],
    token: Annotated[str, Depends(oauth2_scheme)],
    fingerprint: Annotated[str, Cookie(alias=("__Secure-Fgp"))],
):
    from izuna_ytdl.models import User

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, config.JWT_NO_HIMITSU, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            logging.debug("missing sub")
            raise credentials_exception

        fgp_claim = payload.get("user_fingerprint")
        if fgp_claim is None:
            logging.debug("missing fingerprint hash")
            raise credentials_exception

        cookie_hashed = hashlib.sha256(fingerprint.encode()).hexdigest()
        if fgp_claim != cookie_hashed:
            logging.debug("invalid fingerprint")
            raise credentials_exception
    except JWTError as err:
        print("jwterr", err)
        raise credentials_exception

    user = User.get_by_username(session, username=username)
    if user is None:
        print("none user")
        raise credentials_exception

    return user


def create_access_token(
    data: dict, expires_delta: timedelta | None = timedelta(minutes=15)
):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.JWT_NO_HIMITSU, ALGORITHM)
    return encoded_jwt


def generate_fingerprint():
    random_bytes = os.urandom(64)
    return base64.b64encode(random_bytes).decode()

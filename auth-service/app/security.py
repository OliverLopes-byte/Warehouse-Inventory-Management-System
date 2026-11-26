import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated, Callable

import jwt
from fastapi import Depends, Header, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy import select

from app.config import get_settings
from app.database import Database
from app.models import Role, User


bearer = OAuth2PasswordBearer(tokenUrl="/api/auth/auth/login")
passwords = PasswordHash.recommended()
DUMMY_HASH = passwords.hash(secrets.token_urlsafe(32))


def invalid_credentials() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Invalid credentials or inactive account.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def create_token(user_id: int) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user_id),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "exp": now + timedelta(minutes=settings.token_minutes),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )


def current_user(token: Annotated[str, Depends(bearer)], db: Database) -> User:
    settings = get_settings()
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["sub", "iss", "aud", "iat", "exp"]},
        )
        user_id = int(claims["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise invalid_credentials() from None
    if not 0 < user_id <= 2_147_483_647:
        raise invalid_credentials()
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise invalid_credentials()
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require_roles(*allowed: Role) -> Callable:
    def check(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise HTTPException(403, "Your role cannot perform this action.")
        return user
    return check


Admin = Annotated[User, Depends(require_roles(Role.ADMIN))]


def service_access(
    x_service_token: Annotated[str | None, Header(alias="X-Service-Token")] = None,
) -> None:
    expected = get_settings().service_token
    if x_service_token is None or not secrets.compare_digest(x_service_token, expected):
        raise HTTPException(403, "Service credentials are invalid.")


def decode_current(token: str, db: Database) -> User:
    settings = get_settings()
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["sub", "iss", "aud", "iat", "exp"]},
        )
        user_id = int(claims["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise invalid_credentials() from None
    if not 0 < user_id <= 2_147_483_647:
        raise invalid_credentials()
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise invalid_credentials()
    return user

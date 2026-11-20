import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash

from app.config import JWT_AUDIENCE, JWT_ISSUER, get_settings
from app.db import Database
from app.models import Role, User


bearer = OAuth2PasswordBearer(tokenUrl="auth/login")
passwords = PasswordHash.recommended()
DUMMY_HASH = passwords.hash(secrets.token_urlsafe())


def invalid_credentials():
    return HTTPException(
        status_code=401,
        detail="Invalid credentials or inactive account.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def create_token(user_id: int) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(user_id),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(minutes=settings.token_minutes),
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm="HS256")


def current_user(token: Annotated[str, Depends(bearer)], db: Database) -> User:
    try:
        claims = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=["HS256"],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
            options={"require": ["sub", "iss", "aud", "iat", "exp"]},
        )
        user_id = int(claims["sub"])
    except (jwt.InvalidTokenError, ValueError):
        raise invalid_credentials() from None

    # Read the current account on each request so deactivation affects issued tokens.
    if user_id <= 0 or user_id > 2_147_483_647:
        raise invalid_credentials()
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise invalid_credentials()
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require_roles(*allowed: Role):
    def check(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise HTTPException(status_code=403, detail="Your role cannot perform this action.")
        return user

    return check


Admin = Annotated[User, Depends(require_roles(Role.ADMIN))]
Manager = Annotated[User, Depends(require_roles(Role.WAREHOUSE_MANAGER))]
Clerk = Annotated[User, Depends(require_roles(Role.STORE_CLERK))]
OrderReader = Annotated[User, Depends(require_roles(Role.WAREHOUSE_MANAGER, Role.STORE_CLERK))]

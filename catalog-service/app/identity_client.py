from typing import Annotated, Callable

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr

from app.config import get_settings


bearer = OAuth2PasswordBearer(tokenUrl="/api/auth/auth/login")


class Caller(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    warehouse_id: int | None
    is_active: bool


def current_user(token: Annotated[str, Depends(bearer)]) -> Caller:
    settings = get_settings()
    try:
        response = httpx.post(
            f"{settings.auth_url}/internal/introspect",
            headers={"Authorization": f"Bearer {token}", "X-Service-Token": settings.service_token},
            timeout=settings.upstream_timeout,
        )
    except httpx.RequestError:
        raise HTTPException(503, "Auth service is unavailable.") from None
    if response.status_code == 401:
        raise HTTPException(401, "Invalid credentials or inactive account.", headers={"WWW-Authenticate": "Bearer"})
    if response.status_code != 200:
        raise HTTPException(503, "Auth service could not validate the current account.")
    try:
        return Caller.model_validate(response.json())
    except ValueError:
        raise HTTPException(503, "Auth service returned an invalid identity response.") from None


CurrentUser = Annotated[Caller, Depends(current_user)]


def require_roles(*allowed: str) -> Callable:
    def check(user: CurrentUser) -> Caller:
        if user.role not in allowed:
            raise HTTPException(403, "Your role cannot perform this action.")
        return user
    return check


Admin = Annotated[Caller, Depends(require_roles("ADMIN"))]
ADMIN = "ADMIN"

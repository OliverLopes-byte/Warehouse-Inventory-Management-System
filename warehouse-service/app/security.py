import secrets
from typing import Annotated

from fastapi import Header, HTTPException

from app.config import get_settings


def service_access(
    x_service_token: Annotated[str | None, Header(alias="X-Service-Token")] = None,
) -> None:
    expected = get_settings().service_token
    if x_service_token is None or not secrets.compare_digest(x_service_token, expected):
        raise HTTPException(403, "Service credentials are invalid.")

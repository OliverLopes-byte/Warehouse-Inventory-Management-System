import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    database_url: str
    auth_url: str
    service_token: str
    upstream_timeout: float


@lru_cache
def get_settings() -> Settings:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", interpolate=False)
    database_url = os.getenv("CATALOG_DATABASE_URL", "")
    token = os.getenv("AUTH_SERVICE_TOKEN", "")
    timeout = float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", "3"))
    if (
        not database_url
        or len(token) < 32
        or token.lower().startswith(("replace-", "change-me"))
        or timeout <= 0
    ):
        raise ValueError("Set CATALOG_DATABASE_URL, a 32-character AUTH_SERVICE_TOKEN, and a positive timeout.")
    return Settings(
        database_url=database_url,
        auth_url=os.getenv("AUTH_SERVICE_URL", "http://127.0.0.1:8001").rstrip("/"),
        service_token=token,
        upstream_timeout=timeout,
    )

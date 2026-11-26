import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
@dataclass(frozen=True)
class Settings:
    database_url: str
    jwt_secret: str
    jwt_issuer: str
    jwt_audience: str
    token_minutes: int
    service_token: str
    catalog_url: str
    upstream_timeout: float


@lru_cache
def get_settings() -> Settings:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", interpolate=False)
    secret = os.getenv("JWT_SECRET", "")
    service_token = os.getenv("AUTH_SERVICE_TOKEN", "")
    if len(secret.encode("utf-8")) < 32 or secret.lower().startswith(("replace-", "change-me")):
        raise ValueError("Set JWT_SECRET to at least 32 random bytes; do not use the example placeholder.")
    if len(service_token) < 32 or service_token.lower().startswith(("replace-", "change-me")):
        raise ValueError("Set AUTH_SERVICE_TOKEN to a 32-character shared secret; do not use the example placeholder.")
    database_url = os.getenv("AUTH_DATABASE_URL", "")
    if not database_url:
        raise ValueError("AUTH_DATABASE_URL must point to warehouse_identity.")
    minutes = int(os.getenv("TOKEN_MINUTES", "60"))
    timeout = float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", "3"))
    if minutes < 1 or timeout <= 0:
        raise ValueError("Token lifetime and upstream timeout must be positive.")
    return Settings(
        database_url=database_url,
        jwt_secret=secret,
        jwt_issuer=os.getenv("JWT_ISSUER", "warehouse-api"),
        jwt_audience=os.getenv("JWT_AUDIENCE", "warehouse-client"),
        token_minutes=minutes,
        service_token=service_token,
        catalog_url=os.getenv("CATALOG_SERVICE_URL", "http://127.0.0.1:8002").rstrip("/"),
        upstream_timeout=timeout,
    )

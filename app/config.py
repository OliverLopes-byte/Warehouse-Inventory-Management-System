import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
JWT_ISSUER = "warehouse-api"
JWT_AUDIENCE = "warehouse-client"


@dataclass(frozen=True, repr=False)
class Settings:
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    jwt_secret: str
    token_minutes: int
    fast_units: int
    slow_units: int
    expiry_days: int

    @property
    def database_url(self) -> URL:
        return URL.create(
            "postgresql+psycopg",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )


@lru_cache
def get_settings() -> Settings:
    load_dotenv(ENV_FILE, interpolate=False)
    secret = os.getenv("WAREHOUSE_JWT_SECRET", "")
    if len(secret.encode("utf-8")) < 32:
        raise ValueError("Set a random WAREHOUSE_JWT_SECRET of at least 32 bytes. See README.md.")

    settings = Settings(
        db_host=os.getenv("WAREHOUSE_DB_HOST", "127.0.0.1"),
        db_port=int(os.getenv("WAREHOUSE_DB_PORT", "5432")),
        db_name=os.getenv("WAREHOUSE_DB_NAME", "warehouse_inventory"),
        db_user=os.getenv("WAREHOUSE_DB_USER", "postgres"),
        db_password=os.getenv("WAREHOUSE_DB_PASSWORD", ""),
        jwt_secret=secret,
        token_minutes=int(os.getenv("WAREHOUSE_TOKEN_MINUTES", "60")),
        fast_units=int(os.getenv("WAREHOUSE_FAST_UNITS", "20")),
        slow_units=int(os.getenv("WAREHOUSE_SLOW_UNITS", "5")),
        expiry_days=int(os.getenv("WAREHOUSE_EXPIRY_DAYS", "30")),
    )
    if not settings.db_name or settings.db_name in {"postgres", "template0", "template1"}:
        raise ValueError("Choose a dedicated warehouse database name.")
    if not 1 <= settings.db_port <= 65535:
        raise ValueError("The PostgreSQL port must be between 1 and 65535.")
    if not 0 <= settings.slow_units < settings.fast_units:
        raise ValueError("The slow-mover cutoff must be nonnegative and below the fast cutoff.")
    if settings.token_minutes < 1 or settings.expiry_days < 0:
        raise ValueError("Use a positive token lifetime and a nonnegative expiry window.")
    return settings

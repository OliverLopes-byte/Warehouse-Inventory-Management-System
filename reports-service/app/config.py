import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    auth_url: str
    catalog_url: str
    warehouse_url: str
    service_token: str
    upstream_timeout: float
    expiry_days: int
    fast_units: int
    slow_units: int


@lru_cache
def get_settings() -> Settings:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", interpolate=False)
    token = os.getenv("AUTH_SERVICE_TOKEN", "")
    timeout = float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", "5"))
    expiry_days = int(os.getenv("EXPIRY_DAYS", "30"))
    fast_units = int(os.getenv("FAST_UNITS", "20"))
    slow_units = int(os.getenv("SLOW_UNITS", "5"))
    if (
        len(token) < 32
        or token.lower().startswith(("replace-", "change-me"))
        or timeout <= 0
        or expiry_days < 0
        or not 0 <= slow_units < fast_units
    ):
        raise ValueError("Set the shared service token and valid positive report settings.")
    return Settings(
        auth_url=os.getenv("AUTH_SERVICE_URL", "http://127.0.0.1:8001").rstrip("/"),
        catalog_url=os.getenv("CATALOG_SERVICE_URL", "http://127.0.0.1:8002").rstrip("/"),
        warehouse_url=os.getenv("WAREHOUSE_SERVICE_URL", "http://127.0.0.1:8003").rstrip("/"),
        service_token=token,
        upstream_timeout=timeout,
        expiry_days=expiry_days,
        fast_units=fast_units,
        slow_units=slow_units,
    )

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    upstream_timeout: float
    upstreams: dict[str, str]


@lru_cache
def get_settings() -> Settings:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", interpolate=False)
    timeout = float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", "5"))
    port = int(os.getenv("GATEWAY_PORT", "8000"))
    if timeout <= 0 or not 1 <= port <= 65535:
        raise ValueError("Gateway port and upstream timeout must be valid.")
    return Settings(
        host=os.getenv("GATEWAY_HOST", "127.0.0.1"),
        port=port,
        upstream_timeout=timeout,
        upstreams={
            "auth": os.getenv("AUTH_SERVICE_URL", "http://127.0.0.1:8001").rstrip("/"),
            "catalog": os.getenv("CATALOG_SERVICE_URL", "http://127.0.0.1:8002").rstrip("/"),
            "warehouse": os.getenv("WAREHOUSE_SERVICE_URL", "http://127.0.0.1:8003").rstrip("/"),
            "reports": os.getenv("REPORTS_SERVICE_URL", "http://127.0.0.1:8004").rstrip("/"),
        },
    )

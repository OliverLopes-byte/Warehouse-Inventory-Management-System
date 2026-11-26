import httpx
from fastapi import HTTPException

from app.config import get_settings


def active_warehouse(warehouse_id: int) -> dict:
    settings = get_settings()
    try:
        response = httpx.get(
            f"{settings.catalog_url}/internal/warehouses/{warehouse_id}",
            headers={"X-Service-Token": settings.service_token},
            timeout=settings.upstream_timeout,
        )
    except httpx.RequestError:
        raise HTTPException(503, "Catalog service is unavailable.") from None
    if response.status_code == 404:
        raise HTTPException(422, "Choose an active home warehouse.")
    if response.status_code >= 500:
        raise HTTPException(503, "Catalog service is unavailable.")
    if response.status_code != 200:
        raise HTTPException(503, "Catalog reference validation failed.")
    warehouse = response.json()
    if not warehouse.get("is_active"):
        raise HTTPException(422, "Choose an active home warehouse.")
    return warehouse

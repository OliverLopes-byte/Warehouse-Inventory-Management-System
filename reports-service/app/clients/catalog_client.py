import httpx
from fastapi import HTTPException

from app.config import get_settings


PRODUCT_PAGE_SIZE = 500
MAX_PRODUCT_PAGES = 200


def _get(path: str, **params):
    settings = get_settings()
    try:
        response = httpx.get(
            f"{settings.catalog_url}{path}",
            params=params or None,
            headers={"X-Service-Token": settings.service_token},
            timeout=settings.upstream_timeout,
        )
    except httpx.RequestError:
        raise HTTPException(503, "Catalog service is unavailable.") from None
    if response.status_code != 200:
        raise HTTPException(503, "Catalog service could not provide report data.")
    return response.json()


def products(*, active_only: bool) -> list[dict]:
    result: list[dict] = []
    for page in range(1, MAX_PRODUCT_PAGES + 2):
        rows = _get(
            "/internal/products",
            active_only=active_only,
            page=page,
            size=PRODUCT_PAGE_SIZE,
        )
        if page > MAX_PRODUCT_PAGES:
            if rows:
                raise HTTPException(503, "Catalog product result exceeds the bounded report limit.")
            return result
        result.extend(rows)
        if len(rows) < PRODUCT_PAGE_SIZE:
            return result
    raise HTTPException(503, "Catalog product result exceeds the bounded report limit.")


def warehouses() -> list[dict]:
    return _get("/internal/warehouses", active_only=False)


def active_warehouse(warehouse_id: int) -> dict:
    settings = get_settings()
    try:
        response = httpx.get(
            f"{settings.catalog_url}/internal/warehouses/{warehouse_id}",
            params={"active_only": "true"},
            headers={"X-Service-Token": settings.service_token},
            timeout=settings.upstream_timeout,
        )
    except httpx.RequestError:
        raise HTTPException(503, "Catalog service is unavailable.") from None
    if response.status_code == 404:
        raise HTTPException(403, "An active home warehouse is required.")
    if response.status_code != 200:
        raise HTTPException(503, "Catalog service could not validate the home warehouse.")
    return response.json()

import httpx
from fastapi import HTTPException

from app.clients.identity_client import Caller
from app.config import get_settings


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
    if response.status_code >= 500 or response.status_code in (401, 403):
        raise HTTPException(503, "Catalog reference validation is unavailable.")
    return response


def home_warehouse(user: Caller) -> dict:
    if user.warehouse_id is None:
        raise HTTPException(403, "An active home warehouse is required.")
    response = _get(f"/internal/warehouses/{user.warehouse_id}", active_only=True)
    if response.status_code == 404:
        raise HTTPException(403, "An active home warehouse is required.")
    if response.status_code != 200:
        raise HTTPException(503, "Catalog reference validation failed.")
    return response.json()


def warehouse(warehouse_id: int, *, active_only: bool = True) -> dict:
    response = _get(f"/internal/warehouses/{warehouse_id}", active_only=active_only)
    if response.status_code == 404:
        raise HTTPException(404, "Warehouse not found.")
    if response.status_code != 200:
        raise HTTPException(503, "Catalog reference validation failed.")
    return response.json()


def warehouses(*, active_only: bool = False) -> list[dict]:
    response = _get("/internal/warehouses", active_only=active_only)
    if response.status_code != 200:
        raise HTTPException(503, "Catalog reference lookup failed.")
    return response.json()


def supplier(supplier_id: int, *, active_only: bool = True) -> dict:
    response = _get(f"/internal/suppliers/{supplier_id}", active_only=active_only)
    if response.status_code == 404:
        raise HTTPException(422, "Choose an active supplier.")
    if response.status_code != 200:
        raise HTTPException(503, "Catalog reference validation failed.")
    return response.json()


def products(product_ids: set[int], *, active_only: bool = True) -> list[dict]:
    if not product_ids:
        return []
    response = _get("/internal/products", ids=sorted(product_ids), active_only=active_only)
    if response.status_code != 200:
        raise HTTPException(503, "Catalog product lookup failed.")
    found = response.json()
    if {row["id"] for row in found} != product_ids:
        raise HTTPException(422, "One or more product references are unavailable.")
    return found


def bins(bin_ids: set[int], *, warehouse_id: int) -> list[dict]:
    if not bin_ids:
        return []
    response = _get("/internal/bins", ids=sorted(bin_ids), warehouse_id=warehouse_id)
    if response.status_code != 200:
        raise HTTPException(503, "Catalog bin lookup failed.")
    found = response.json()
    if {row["id"] for row in found} != bin_ids:
        raise HTTPException(422, "Use bins from your warehouse.")
    return found

import httpx
from datetime import date
from fastapi import HTTPException

from app.config import get_settings


def _get(path: str, **params):
    settings = get_settings()
    params = {key: value for key, value in params.items() if value is not None}
    try:
        response = httpx.get(
            f"{settings.warehouse_url}{path}",
            params=params or None,
            headers={"X-Service-Token": settings.service_token},
            timeout=settings.upstream_timeout,
        )
    except httpx.RequestError:
        raise HTTPException(503, "Warehouse service is unavailable.") from None
    if response.status_code != 200:
        raise HTTPException(503, "Warehouse service could not provide report data.")
    return response.json()


def balances(*, warehouse_id: int | None = None) -> list[dict]:
    rows: list[dict] = []
    for page in range(1, 201):
        envelope = _get(
            "/stock/internal/balances",
            warehouse_id=warehouse_id,
            page=page,
            size=500,
        )
        rows.extend(envelope["items"])
        if page * envelope["size"] >= envelope["total"]:
            return rows
    raise HTTPException(503, "Warehouse balance result exceeds the bounded report limit.")


def issue_totals(start: date, end: date) -> dict[int, object]:
    rows = _get("/stock/internal/issue-totals", **{"from": start.isoformat(), "to": end.isoformat()})
    return {row["product_id"]: row["units"] for row in rows}

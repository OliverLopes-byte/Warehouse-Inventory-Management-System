from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated
from fastapi import HTTPException, Query
from sqlalchemy import func, select
from app.models import StockLedger, User, Warehouse
PageNumber = Annotated[int, Query(ge=1, le=1_000_000)]
PageSize = Annotated[int, Query(ge=1, le=100)]
StartDate = Annotated[date | None, Query(alias="from")]
EndDate = Annotated[date | None, Query(alias="to")]


def required_row(db, model, row_id: int, label: str):
    row = db.get(model, row_id)
    if row is None:
        raise HTTPException(404, f"{label} not found.")
    return row


def home_warehouse(db, user: User) -> Warehouse:
    warehouse = db.get(Warehouse, user.warehouse_id) if user.warehouse_id else None
    if warehouse is None or not warehouse.is_active:
        raise HTTPException(403, "An active home warehouse is required.")
    return warehouse


def page_of(db, statement, page: int, size: int, *, mappings: bool = False):
    total = db.scalar(select(func.count()).select_from(statement.order_by(None).subquery()))
    result = db.execute(statement.offset((page - 1) * size).limit(size))
    items = result.mappings().all() if mappings else result.scalars().all()
    return {"items": items, "page": page, "size": size, "total": total}


def ledger_dates(statement, start: date | None, end: date | None):
    if start is not None and end is not None and start > end:
        raise HTTPException(422, "The start date must be on or before the end date.")
    if start is not None:
        statement = statement.where(
            StockLedger.created_at >= datetime.combine(start, time.min, timezone.utc)
        )
    if end is not None and end < date.max:
        # The exclusive next midnight includes all times on the chosen end date.
        stop = datetime.combine(end + timedelta(days=1), time.min, timezone.utc)
        statement = statement.where(StockLedger.created_at < stop)
    return statement

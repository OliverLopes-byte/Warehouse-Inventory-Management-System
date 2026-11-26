from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.clients.catalog_client import home_warehouse
from app.clients.identity_client import Caller
from app.models import Movement, StockBalance, StockLedger


def home_for(user: Caller) -> dict:
    return home_warehouse(user)


def scoped_warehouse_id(user: Caller, requested: int | None) -> int | None:
    if user.role == "ADMIN":
        return requested
    home = home_for(user)
    if requested is not None and requested != home["id"]:
        raise HTTPException(403, "You can only view stock for your home warehouse.")
    return home["id"]


def page_of(db: Session, statement, page: int, size: int, *, mappings: bool = False):
    total = db.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
    result = db.execute(statement.offset((page - 1) * size).limit(size))
    items = result.mappings().all() if mappings else result.scalars().all()
    return {"items": items, "page": page, "size": size, "total": total}


def ledger_dates(statement, start: date | None, end: date | None):
    if start is not None and end is not None and start > end:
        raise HTTPException(422, "The start date must be on or before the end date.")
    if start is not None:
        statement = statement.where(StockLedger.created_at >= datetime.combine(start, time.min, timezone.utc))
    if end is not None and end < date.max:
        statement = statement.where(
            StockLedger.created_at < datetime.combine(end + timedelta(days=1), time.min, timezone.utc)
        )
    return statement


def lock_balances(db: Session, keys: list[tuple[int, int]]) -> dict[tuple[int, int], StockBalance]:
    locked = {}
    for warehouse_id, product_id in sorted(set(keys)):
        statement = insert(StockBalance).values(warehouse_id=warehouse_id, product_id=product_id)
        db.execute(statement.on_conflict_do_nothing(constraint="uq_balance_position"))
        row_statement = (
            select(StockBalance)
            .where(StockBalance.warehouse_id == warehouse_id, StockBalance.product_id == product_id)
            .with_for_update()
        )
        locked[(warehouse_id, product_id)] = db.scalars(
            row_statement.execution_options(populate_existing=True)
        ).one()
    return locked


def write_movement(
    db: Session,
    balance: StockBalance,
    movement: Movement,
    delta: Decimal,
    reference_type: str,
    reference_id: str,
    actor_id: int,
    reason: str | None = None,
) -> StockLedger:
    after = balance.quantity + delta
    if after < 0:
        raise HTTPException(409, "Insufficient available stock.")
    balance.quantity = after
    balance.position_seq += 1
    if after == 0:
        balance.expiry_on = None
    entry = StockLedger(
        product_id=balance.product_id,
        warehouse_id=balance.warehouse_id,
        movement_type=movement.value,
        qty_delta=delta,
        reference_type=reference_type,
        reference_id=reference_id,
        balance_after=after,
        position_seq=balance.position_seq,
        reason=reason,
        created_by=actor_id,
    )
    db.add(entry)
    db.flush()
    return entry

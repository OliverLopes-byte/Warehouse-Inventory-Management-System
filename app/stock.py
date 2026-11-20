from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Movement, StockBalance, StockLedger


def lock_balances(db: Session, keys: list[tuple[int, int]]) -> dict[tuple[int, int], StockBalance]:
    """Lock positions in (warehouse, product) order until the caller finishes the transaction."""
    balances = {}
    for warehouse_id, product_id in sorted(set(keys)):
        # A missing row cannot be locked. Create zero stock if this is a new position.
        create = insert(StockBalance).values(warehouse_id=warehouse_id, product_id=product_id)
        db.execute(create.on_conflict_do_nothing(constraint="uq_balance_position"))

        statement = select(StockBalance).where(
            StockBalance.warehouse_id == warehouse_id, StockBalance.product_id == product_id
        ).with_for_update()
        balances[(warehouse_id, product_id)] = db.scalars(
            statement.execution_options(populate_existing=True)
        ).one()
    return balances


def write_movement(
    db: Session, balance: StockBalance, movement: Movement, delta: Decimal,
    reference_type: str, reference_id: str, actor_id: int, reason: str | None = None,
) -> StockLedger:
    """Update a locked balance and add its matching history row without committing."""
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
        movement_type=movement,
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

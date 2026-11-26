from datetime import date
from decimal import Decimal
from uuid import uuid4
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from app.clients.catalog_client import home_warehouse, products, warehouse, warehouses
from app.clients.identity_client import Clerk, CurrentUser, Manager
from app.database import Database
from app.models import Movement, StockBalance, StockLedger
from app.schemas import (
    AdjustmentInput,
    BalanceOut,
    ExpiryInput,
    InternalBalance,
    IssueInput,
    LedgerOut,
    Page,
    TransferInput,
    TransferOut,
)
from app.security import service_access
from app.services.stock import ledger_dates, lock_balances, page_of, scoped_warehouse_id, write_movement


router = APIRouter(prefix="/stock", tags=["Stock"])


@router.post("/issue", response_model=LedgerOut, status_code=status.HTTP_201_CREATED)
def issue(body: IssueInput, db: Database, clerk: Clerk):
    home = home_warehouse(clerk)
    products({body.product_id}, active_only=False)
    key = (home["id"], body.product_id)
    balance = lock_balances(db, [key])[key]
    entry = write_movement(
        db, balance, Movement.ISSUE, -body.quantity, "REQUISITION",
        body.requisition_no.strip().upper(), clerk.id,
    )
    db.commit()
    return entry


@router.post("/transfer", response_model=TransferOut, status_code=status.HTTP_201_CREATED)
def transfer(body: TransferInput, db: Database, manager: Manager):
    home = home_warehouse(manager)
    if body.source_warehouse_id != home["id"]:
        raise HTTPException(403, "Transfers must start at your home warehouse.")
    if body.destination_warehouse_id == home["id"]:
        raise HTTPException(422, "Choose a different destination warehouse.")
    destination = warehouse(body.destination_warehouse_id, active_only=True)
    products({body.product_id}, active_only=False)
    source_key = (home["id"], body.product_id)
    destination_key = (destination["id"], body.product_id)
    balances = lock_balances(db, [source_key, destination_key])
    reference = str(uuid4())
    outgoing = write_movement(
        db, balances[source_key], Movement.TRANSFER_OUT, -body.quantity,
        "TRANSFER", reference, manager.id,
    )
    incoming = write_movement(
        db, balances[destination_key], Movement.TRANSFER_IN, body.quantity,
        "TRANSFER", reference, manager.id,
    )
    db.commit()
    return {"reference_id": reference, "out": outgoing, "incoming": incoming}


@router.post("/adjust", response_model=LedgerOut, status_code=status.HTTP_201_CREATED)
def adjust(body: AdjustmentInput, db: Database, manager: Manager):
    home = home_warehouse(manager)
    products({body.product_id}, active_only=False)
    reason = body.reason.strip()
    if not reason:
        raise HTTPException(422, "An adjustment reason is required.")
    key = (home["id"], body.product_id)
    balance = lock_balances(db, [key])[key]
    delta = body.counted_quantity - balance.quantity
    if delta == 0:
        raise HTTPException(409, "The count matches current stock. No adjustment was posted.")
    entry = write_movement(
        db, balance, Movement.ADJUSTMENT, delta, "COUNT", str(uuid4()), manager.id, reason,
    )
    db.commit()
    return entry


@router.put("/expiry/{product_id}", response_model=ExpiryInput)
def set_expiry(product_id: int, body: ExpiryInput, db: Database, manager: Manager):
    home = home_warehouse(manager)
    products({product_id}, active_only=False)
    key = (home["id"], product_id)
    balance = lock_balances(db, [key])[key]
    if body.expiry_on is not None and balance.quantity == 0:
        raise HTTPException(409, "Record expiry only for stock on hand.")
    balance.expiry_on = body.expiry_on
    db.commit()
    return body


@router.get("/balance", response_model=Page[BalanceOut])
def stock_balance(
    db: Database,
    user: CurrentUser,
    product_id: Annotated[int | None, Query(gt=0)] = None,
    warehouse_id: Annotated[int | None, Query(gt=0)] = None,
    page: Annotated[int, Query(ge=1, le=1_000_000)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 25,
):
    warehouse_scope = scoped_warehouse_id(user, warehouse_id)
    if product_id is not None:
        product = products({product_id}, active_only=False)[0]
        locations = (
            [warehouse(warehouse_scope, active_only=False)]
            if warehouse_scope is not None
            else warehouses(active_only=False)
        )
        statement = select(StockBalance).where(StockBalance.product_id == product_id)
        if warehouse_scope is not None:
            statement = statement.where(StockBalance.warehouse_id == warehouse_scope)
        existing = {
            row.warehouse_id: row
            for row in db.scalars(statement).all()
        }
        rows = [
            {
                "product_id": product_id,
                "sku": product["sku"],
                "product_name": product["name"],
                "warehouse_id": location["id"],
                "warehouse_code": location["code"],
                "quantity": existing[location["id"]].quantity if location["id"] in existing else Decimal("0"),
                "position_seq": existing[location["id"]].position_seq if location["id"] in existing else 0,
                "expiry_on": existing[location["id"]].expiry_on if location["id"] in existing else None,
            }
            for location in locations
        ]
        rows.sort(key=lambda row: (row["sku"], row["warehouse_code"], row["product_id"]))
        total = len(rows)
        items = rows[(page - 1) * size : page * size]
        return {"items": items, "page": page, "size": size, "total": total}

    statement = select(StockBalance)
    if warehouse_scope is not None:
        statement = statement.where(StockBalance.warehouse_id == warehouse_scope)
    statement = statement.order_by(StockBalance.product_id, StockBalance.warehouse_id)
    result = page_of(db, statement, page, size)
    balances = result["items"]
    product_rows = products({row.product_id for row in balances}, active_only=False)
    product_map = {row["id"]: row for row in product_rows}
    location_rows = warehouses(active_only=False)
    location_map = {row["id"]: row for row in location_rows}
    result["items"] = [
        {
            "product_id": row.product_id,
            "sku": product_map[row.product_id]["sku"],
            "product_name": product_map[row.product_id]["name"],
            "warehouse_id": row.warehouse_id,
            "warehouse_code": location_map[row.warehouse_id]["code"],
            "quantity": row.quantity,
            "position_seq": row.position_seq,
            "expiry_on": row.expiry_on,
        }
        for row in balances
    ]
    return result


@router.get("/ledger", response_model=Page[LedgerOut])
def stock_ledger(
    db: Database,
    user: CurrentUser,
    product_id: Annotated[int | None, Query(gt=0)] = None,
    warehouse_id: Annotated[int | None, Query(gt=0)] = None,
    start: Annotated[date | None, Query(alias="from")] = None,
    end: Annotated[date | None, Query(alias="to")] = None,
    page: Annotated[int, Query(ge=1, le=1_000_000)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 25,
):
    warehouse_scope = scoped_warehouse_id(user, warehouse_id)
    statement = ledger_dates(select(StockLedger), start, end)
    if product_id is not None:
        statement = statement.where(StockLedger.product_id == product_id)
    if warehouse_scope is not None:
        statement = statement.where(StockLedger.warehouse_id == warehouse_scope)
    return page_of(db, statement.order_by(StockLedger.created_at.desc(), StockLedger.id.desc()), page, size)


@router.get(
    "/internal/balances",
    response_model=Page[InternalBalance],
    dependencies=[Depends(service_access)],
    include_in_schema=False,
)
def internal_balances(
    db: Database,
    warehouse_id: int | None = Query(default=None, gt=0),
    page: int = Query(default=1, ge=1, le=1_000_000),
    size: int = Query(default=500, ge=1, le=500),
):
    statement = select(StockBalance)
    if warehouse_id is not None:
        statement = statement.where(StockBalance.warehouse_id == warehouse_id)
    return page_of(db, statement.order_by(StockBalance.warehouse_id, StockBalance.product_id), page, size)


@router.get(
    "/internal/issue-totals",
    dependencies=[Depends(service_access)],
    include_in_schema=False,
)
def internal_issue_totals(
    db: Database,
    start: Annotated[date, Query(alias="from")],
    end: Annotated[date, Query(alias="to")],
):
    statement = ledger_dates(
        select(StockLedger.product_id, func.sum(-StockLedger.qty_delta).label("units"))
        .where(StockLedger.movement_type == Movement.ISSUE.value)
        .group_by(StockLedger.product_id),
        start,
        end,
    )
    return db.execute(statement.order_by(StockLedger.product_id)).mappings().all()

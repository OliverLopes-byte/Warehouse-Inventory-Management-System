from decimal import Decimal
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import and_, func, select

from app.db import Database
from app.models import Movement, Product, StockBalance, StockLedger, Warehouse
from app.queries import EndDate, PageNumber, PageSize, StartDate, home_warehouse, ledger_dates, page_of, required_row
from app.schemas import AdjustmentInput, BalanceOut, ExpiryInput, IssueInput, LedgerOut, Page, TransferInput, TransferOut
from app.security import Clerk, CurrentUser, Manager
from app.stock import lock_balances, write_movement


router = APIRouter(prefix="/stock", tags=["Stock"])


@router.post("/issue", response_model=LedgerOut, status_code=status.HTTP_201_CREATED)
def issue(body: IssueInput, db: Database, clerk: Clerk):
    warehouse = home_warehouse(db, clerk)
    required_row(db, Product, body.product_id, "Product")
    key = (warehouse.id, body.product_id)
    balance = lock_balances(db, [key])[key]
    entry = write_movement(
        db, balance, Movement.ISSUE, -body.quantity, "REQUISITION", body.requisition_no, clerk.id,
    )
    db.commit()
    return entry


@router.post("/transfer", response_model=TransferOut, status_code=status.HTTP_201_CREATED)
def transfer(body: TransferInput, db: Database, manager: Manager):
    home = home_warehouse(db, manager)
    if body.source_warehouse_id != home.id:
        raise HTTPException(403, "Transfers must start at your home warehouse.")
    if body.destination_warehouse_id == home.id:
        raise HTTPException(422, "Choose a different destination warehouse.")
    destination = required_row(db, Warehouse, body.destination_warehouse_id, "Destination warehouse")
    if not destination.is_active:
        raise HTTPException(422, "Choose an active destination warehouse.")
    required_row(db, Product, body.product_id, "Product")

    source_key = (home.id, body.product_id)
    destination_key = (destination.id, body.product_id)
    balances = lock_balances(db, [source_key, destination_key])
    reference = str(uuid4())
    out = write_movement(
        db, balances[source_key], Movement.TRANSFER_OUT, -body.quantity, "TRANSFER", reference, manager.id,
    )
    incoming = write_movement(
        db, balances[destination_key], Movement.TRANSFER_IN, body.quantity, "TRANSFER", reference, manager.id,
    )
    # Each leg has reached PostgreSQL, but neither is visible as committed until this point.
    db.commit()
    return {"reference_id": reference, "out": out, "incoming": incoming}


@router.post("/adjust", response_model=LedgerOut, status_code=status.HTTP_201_CREATED)
def adjust(body: AdjustmentInput, db: Database, manager: Manager):
    warehouse = home_warehouse(db, manager)
    required_row(db, Product, body.product_id, "Product")
    key = (warehouse.id, body.product_id)
    balance = lock_balances(db, [key])[key]
    delta = body.counted_quantity - balance.quantity
    if delta == 0:
        raise HTTPException(409, "The count matches current stock. No adjustment was posted.")
    entry = write_movement(
        db, balance, Movement.ADJUSTMENT, delta, "COUNT", str(uuid4()), manager.id, body.reason,
    )
    db.commit()
    return entry


@router.put("/expiry/{product_id}", response_model=ExpiryInput)
def set_expiry(product_id: int, body: ExpiryInput, db: Database, manager: Manager):
    warehouse = home_warehouse(db, manager)
    required_row(db, Product, product_id, "Product")
    key = (warehouse.id, product_id)
    balance = lock_balances(db, [key])[key]
    if body.expiry_on is not None and balance.quantity == 0:
        raise HTTPException(409, "Record expiry only for stock on hand.")
    balance.expiry_on = body.expiry_on
    db.commit()
    return body


@router.get("/balance", response_model=Page[BalanceOut])
def stock_balance(
    db: Database, user: CurrentUser,
    product_id: Annotated[int | None, Query(gt=0)] = None,
    warehouse_id: Annotated[int | None, Query(gt=0)] = None,
    page: PageNumber = 1, size: PageSize = 25,
):
    statement = select(
        Product.id.label("product_id"), Product.sku, Product.name.label("product_name"),
        Warehouse.id.label("warehouse_id"), Warehouse.code.label("warehouse_code"),
        func.coalesce(StockBalance.quantity, Decimal("0")).label("quantity"),
        func.coalesce(StockBalance.position_seq, 0).label("position_seq"), StockBalance.expiry_on,
    )
    if product_id is None:
        statement = statement.select_from(StockBalance).join(Product).join(Warehouse)
    else:
        # For a single product, show zero even at warehouses that never handled it.
        statement = statement.select_from(Warehouse).join(Product, Product.id == product_id).outerjoin(
            StockBalance, and_(StockBalance.warehouse_id == Warehouse.id, StockBalance.product_id == Product.id)
        )
    if warehouse_id is not None:
        statement = statement.where(Warehouse.id == warehouse_id)
    return page_of(db, statement.order_by(Product.sku, Warehouse.code, Product.id), page, size, mappings=True)


@router.get("/ledger", response_model=Page[LedgerOut])
def stock_ledger(
    db: Database, user: CurrentUser,
    product_id: Annotated[int | None, Query(gt=0)] = None,
    warehouse_id: Annotated[int | None, Query(gt=0)] = None,
    start: StartDate = None, end: EndDate = None,
    page: PageNumber = 1, size: PageSize = 25,
):
    statement = ledger_dates(select(StockLedger), start, end)
    if product_id is not None:
        statement = statement.where(StockLedger.product_id == product_id)
    if warehouse_id is not None:
        statement = statement.where(StockLedger.warehouse_id == warehouse_id)
    return page_of(db, statement.order_by(StockLedger.created_at.desc(), StockLedger.id.desc()), page, size)

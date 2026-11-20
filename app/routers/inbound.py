from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import Database
from app.models import Bin, GRN, GRNItem, Movement, POItem, POStatus, Product, PurchaseOrder, Supplier
from app.queries import PageNumber, PageSize, home_warehouse, page_of, required_row
from app.schemas import GRNCreate, GRNOut, POCreate, POOut, Page
from app.security import Clerk, Manager, OrderReader
from app.stock import lock_balances, write_movement


router = APIRouter(tags=["Inbound"])


def warehouse_order(db, order_id: int, warehouse_id: int, *, lock: bool = False):
    statement = select(PurchaseOrder).options(selectinload(PurchaseOrder.items)).where(
        PurchaseOrder.id == order_id, PurchaseOrder.warehouse_id == warehouse_id,
    )
    if lock:
        # All receipt, close and cancel paths lock this same parent before reading line totals.
        statement = statement.with_for_update()
    order = db.scalar(statement)
    if order is None:
        raise HTTPException(404, "Purchase order not found in your warehouse.")
    return order


@router.post("/purchase-orders", response_model=POOut, status_code=status.HTTP_201_CREATED)
def create_order(body: POCreate, db: Database, manager: Manager):
    warehouse = home_warehouse(db, manager)
    supplier = required_row(db, Supplier, body.supplier_id, "Supplier")
    if not supplier.is_active:
        raise HTTPException(422, "Choose an active supplier.")

    product_ids = {line.product_id for line in body.items}
    if len(product_ids) != len(body.items):
        raise HTTPException(422, "Include each product once in a purchase order.")
    available_ids = set(db.scalars(select(Product.id).where(
        Product.id.in_(product_ids), Product.is_deleted.is_(False)
    )))
    if available_ids != product_ids:
        raise HTTPException(422, "All order lines need an active product.")

    lines = [POItem(**line.model_dump()) for line in body.items]
    total = sum(
        (line.ordered_qty * line.unit_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        for line in body.items
    )
    order = PurchaseOrder(
        po_no=body.po_no.upper(), supplier_id=supplier.id, warehouse_id=warehouse.id,
        status=POStatus.OPEN, ordered_on=body.ordered_on, total_amount=total, items=lines,
    )
    db.add(order)
    db.commit()
    return order


@router.get("/purchase-orders", response_model=Page[POOut])
def list_orders(
    db: Database, user: OrderReader,
    po_status: Annotated[POStatus | None, Query(alias="status")] = None,
    supplier_id: Annotated[int | None, Query(gt=0)] = None,
    page: PageNumber = 1, size: PageSize = 25,
):
    warehouse = home_warehouse(db, user)
    statement = select(PurchaseOrder).where(PurchaseOrder.warehouse_id == warehouse.id)
    if po_status is not None:
        statement = statement.where(PurchaseOrder.status == po_status)
    if supplier_id is not None:
        statement = statement.where(PurchaseOrder.supplier_id == supplier_id)
    statement = statement.options(selectinload(PurchaseOrder.items)).order_by(PurchaseOrder.id.desc())
    return page_of(db, statement, page, size)


@router.get("/purchase-orders/{order_id}", response_model=POOut)
def get_order(order_id: int, db: Database, user: OrderReader):
    return warehouse_order(db, order_id, home_warehouse(db, user).id)


def finish_order(db, order_id, manager, next_status: POStatus):
    order = warehouse_order(db, order_id, home_warehouse(db, manager).id, lock=True)
    if order.status == next_status:
        return order
    if order.status in (POStatus.CLOSED, POStatus.CANCELLED):
        raise HTTPException(409, "This purchase order is already final.")
    if next_status == POStatus.CANCELLED and order.status == POStatus.PARTIAL:
        raise HTTPException(409, "Close a partially received order to retain its receipts.")
    order.status = next_status
    db.commit()
    return order


@router.patch("/purchase-orders/{order_id}/close", response_model=POOut)
def close_order(order_id: int, db: Database, manager: Manager):
    return finish_order(db, order_id, manager, POStatus.CLOSED)


@router.patch("/purchase-orders/{order_id}/cancel", response_model=POOut)
def cancel_order(order_id: int, db: Database, manager: Manager):
    return finish_order(db, order_id, manager, POStatus.CANCELLED)


@router.post("/grns", response_model=GRNOut, status_code=status.HTTP_201_CREATED)
def receive_goods(body: GRNCreate, db: Database, clerk: Clerk):
    warehouse = home_warehouse(db, clerk)
    order = warehouse_order(db, body.po_id, warehouse.id, lock=True)
    if order.status not in (POStatus.OPEN, POStatus.PARTIAL):
        raise HTTPException(409, "This purchase order is closed to receipts.")

    po_items = {line.id: line for line in order.items}
    if len({line.po_item_id for line in body.items}) != len(body.items):
        raise HTTPException(422, "Include each purchase order line once per receipt.")
    allowed_bins = set(db.scalars(select(Bin.id).where(Bin.warehouse_id == warehouse.id)))
    for line in body.items:
        po_item = po_items.get(line.po_item_id)
        if po_item is None or line.bin_id not in allowed_bins:
            raise HTTPException(422, "Use lines from this order and bins from your warehouse.")
        if line.qty > po_item.outstanding_qty:
            raise HTTPException(409, "Receipt quantity exceeds the outstanding purchase order quantity.")

    receipt = GRN(grn_no=body.grn_no.upper(), po_id=order.id, received_by=clerk.id, remark=body.remark)
    db.add(receipt)
    db.flush()

    keys = [(warehouse.id, po_items[line.po_item_id].product_id) for line in body.items]
    balances = lock_balances(db, keys)
    for line in body.items:
        po_item = po_items[line.po_item_id]
        po_item.received_qty += line.qty
        receipt.items.append(GRNItem(**line.model_dump(), product_id=po_item.product_id))
        write_movement(
            db, balances[(warehouse.id, po_item.product_id)], Movement.RECEIPT, line.qty,
            "GRN", str(receipt.id), clerk.id,
        )

    order.status = POStatus.CLOSED if all(line.outstanding_qty == 0 for line in order.items) else POStatus.PARTIAL
    db.commit()
    return receipt

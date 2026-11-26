from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.clients.catalog_client import home_warehouse, products, supplier
from app.clients.identity_client import Caller
from app.database import Database
from app.models import POItem, POStatus, PurchaseOrder
from app.schemas import POCreate


def warehouse_order(db: Database, order_id: int, warehouse_id: int, *, lock: bool = False):
    statement = (
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.items))
        .where(PurchaseOrder.id == order_id, PurchaseOrder.warehouse_id == warehouse_id)
    )
    if lock:
        statement = statement.with_for_update(of=PurchaseOrder)
    order = db.scalar(statement)
    if order is None:
        raise HTTPException(404, "Purchase order not found in your warehouse.")
    return order


def create_order(body: POCreate, db: Database, manager: Caller):
    warehouse = home_warehouse(manager)
    supplier(body.supplier_id, active_only=True)
    product_ids = {line.product_id for line in body.items}
    if len(product_ids) != len(body.items):
        raise HTTPException(422, "Include each product once in a purchase order.")
    products(product_ids, active_only=True)
    lines = [POItem(**line.model_dump()) for line in body.items]
    total = sum(
        (line.ordered_qty * line.unit_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        for line in body.items
    )
    order = PurchaseOrder(
        po_no=body.po_no.strip().upper(),
        supplier_id=body.supplier_id,
        warehouse_id=warehouse["id"],
        status=POStatus.OPEN.value,
        ordered_on=body.ordered_on,
        total_amount=total,
        items=lines,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def finish_order(db: Database, order_id: int, manager: Caller, next_status: POStatus):
    order = warehouse_order(db, order_id, home_warehouse(manager)["id"], lock=True)
    if order.status == next_status:
        return order
    if order.status in (POStatus.CLOSED.value, POStatus.CANCELLED.value):
        raise HTTPException(409, "This purchase order is already final.")
    if next_status == POStatus.CANCELLED and order.status == POStatus.PARTIAL.value:
        raise HTTPException(409, "Close a partially received order to retain its receipts.")
    order.status = next_status.value
    db.commit()
    return order

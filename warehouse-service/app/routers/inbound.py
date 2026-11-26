from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.clients.catalog_client import home_warehouse
from app.clients.identity_client import Clerk, Manager, OrderReader
from app.database import Database
from app.models import POStatus, PurchaseOrder
from app.schemas import GRNCreate, GRNOut, Page, POCreate, POOut
from app.services.purchase_orders import create_order, finish_order, warehouse_order
from app.services.receiving import receive_goods
from app.services.stock import page_of


router = APIRouter(tags=["Inbound"])


@router.post("/purchase-orders", response_model=POOut, status_code=status.HTTP_201_CREATED)
def post_order(body: POCreate, db: Database, manager: Manager):
    return create_order(body, db, manager)


@router.get("/purchase-orders", response_model=Page[POOut])
def list_orders(
    db: Database,
    user: OrderReader,
    po_status: Annotated[POStatus | None, Query(alias="status")] = None,
    supplier_id: Annotated[int | None, Query(gt=0)] = None,
    page: Annotated[int, Query(ge=1, le=1_000_000)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 25,
):
    warehouse_id = home_warehouse(user)["id"]
    statement = select(PurchaseOrder).where(PurchaseOrder.warehouse_id == warehouse_id)
    if po_status is not None:
        statement = statement.where(PurchaseOrder.status == po_status.value)
    if supplier_id is not None:
        statement = statement.where(PurchaseOrder.supplier_id == supplier_id)
    statement = statement.options(selectinload(PurchaseOrder.items)).order_by(PurchaseOrder.id.desc())
    return page_of(db, statement, page, size)


@router.get("/purchase-orders/{order_id}", response_model=POOut)
def get_order(order_id: int, db: Database, user: OrderReader):
    return warehouse_order(db, order_id, home_warehouse(user)["id"])


@router.patch("/purchase-orders/{order_id}/close", response_model=POOut)
def close_order(order_id: int, db: Database, manager: Manager):
    return finish_order(db, order_id, manager, POStatus.CLOSED)


@router.patch("/purchase-orders/{order_id}/cancel", response_model=POOut)
def cancel_order(order_id: int, db: Database, manager: Manager):
    return finish_order(db, order_id, manager, POStatus.CANCELLED)


@router.post("/grns", response_model=GRNOut, status_code=status.HTTP_201_CREATED)
def post_receipt(body: GRNCreate, db: Database, clerk: Clerk):
    return receive_goods(body, db, clerk)

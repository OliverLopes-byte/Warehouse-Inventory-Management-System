from datetime import date, datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import and_, case, func, select

from app.config import get_settings
from app.db import Database
from app.models import Movement, Product, StockBalance, StockLedger, Warehouse
from app.queries import home_warehouse, ledger_dates
from app.Schemas import ExpiryOut, MovementAnalysisOut, ReorderOut, ValuationOut
from app.security import Admin, Manager


router = APIRouter()


@router.get("/alerts/reorder", response_model=list[ReorderOut], tags=["Alerts"])
def reorder(db: Database, manager: Manager):
    warehouse = home_warehouse(db, manager)
    quantity = func.coalesce(StockBalance.quantity, 0)
    statement = select(
        Product.id.label("product_id"), Product.sku, Product.name, quantity.label("quantity"), Product.reorder_level,
    ).outerjoin(
        StockBalance, and_(StockBalance.product_id == Product.id, StockBalance.warehouse_id == warehouse.id)
    ).where(Product.is_deleted.is_(False), quantity < Product.reorder_level).order_by(Product.sku)
    return db.execute(statement).mappings().all()


@router.get("/alerts/expiry", response_model=list[ExpiryOut], tags=["Alerts"])
def expiry(db: Database, manager: Manager):
    warehouse = home_warehouse(db, manager)
    today = datetime.now(timezone.utc).date()
    cutoff = today + timedelta(days=get_settings().expiry_days)
    statement = select(
        Product.id.label("product_id"), Product.sku, Product.name, StockBalance.quantity, StockBalance.expiry_on,
        case((StockBalance.expiry_on < today, "EXPIRED"), else_="EXPIRING").label("status"),
    ).join(StockBalance).where(
        StockBalance.warehouse_id == warehouse.id, StockBalance.quantity > 0, StockBalance.expiry_on <= cutoff,
    ).order_by(StockBalance.expiry_on, Product.sku)
    return db.execute(statement).mappings().all()


@router.get("/reports/valuation", response_model=list[ValuationOut], tags=["Reports"])
def valuation(db: Database, admin: Admin):
    statement = select(
        Warehouse.id.label("warehouse_id"), Warehouse.code.label("warehouse_code"),
        Warehouse.name.label("warehouse_name"),
        func.round(func.coalesce(func.sum(StockBalance.quantity * Product.unit_cost), 0), 2).label("value"),
    ).outerjoin(StockBalance).outerjoin(Product).group_by(Warehouse.id).order_by(Warehouse.code)
    return db.execute(statement).mappings().all()


@router.get("/reports/movement-analysis", response_model=list[MovementAnalysisOut], tags=["Reports"])
def movement_analysis(
    db: Database, admin: Admin,
    start: Annotated[date, Query(alias="from")], end: Annotated[date, Query(alias="to")],
):
    settings = get_settings()
    issued = ledger_dates(
        select(StockLedger.product_id, func.sum(-StockLedger.qty_delta).label("units"))
        .where(StockLedger.movement_type == Movement.ISSUE).group_by(StockLedger.product_id), start, end,
    ).subquery()
    units = func.coalesce(issued.c.units, 0)
    classification = case(
        (units >= settings.fast_units, "FAST"), (units <= settings.slow_units, "SLOW"), else_="MEDIUM",
    )
    statement = select(
        Product.id.label("product_id"), Product.sku, Product.name,
        units.label("issued_quantity"), classification.label("classification"),
    ).outerjoin(issued, issued.c.product_id == Product.id).where(
        Product.is_deleted.is_(False) | issued.c.units.is_not(None)
    ).order_by(units.desc(), Product.sku)
    return db.execute(statement).mappings().all()

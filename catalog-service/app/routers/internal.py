from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.database import Database
from app.models import Bin, Product, Supplier, Warehouse
from app.schemas import BinOut, ProductReference, WarehouseOut
from app.security import service_access


router = APIRouter(
    prefix="/internal",
    tags=["Internal"],
    dependencies=[Depends(service_access)],
    include_in_schema=False,
)


@router.get("/products", response_model=list[ProductReference])
def lookup_products(
    db: Database,
    ids: list[int] | None = Query(default=None, max_length=500),
    active_only: bool = True,
    page: int = Query(default=1, ge=1, le=1_000_000),
    size: int = Query(default=100, ge=1, le=500),
):
    statement = select(Product)
    if ids is not None:
        if not ids or any(item <= 0 for item in ids):
            raise HTTPException(422, "Provide one or more positive product IDs.")
        statement = statement.where(Product.id.in_(set(ids)))
    if active_only:
        statement = statement.where(Product.is_deleted.is_(False))
    return db.scalars(statement.order_by(Product.id).offset((page - 1) * size).limit(size)).all()


@router.get("/suppliers/{supplier_id}")
def lookup_supplier(supplier_id: int, db: Database, active_only: bool = True):
    supplier = db.get(Supplier, supplier_id)
    if supplier is None or (active_only and not supplier.is_active):
        raise HTTPException(404, "Supplier not found.")
    return supplier


@router.get("/warehouses", response_model=list[WarehouseOut])
def lookup_warehouses(db: Database, active_only: bool = False):
    statement = select(Warehouse)
    if active_only:
        statement = statement.where(Warehouse.is_active.is_(True))
    return db.scalars(statement.order_by(Warehouse.id)).all()


@router.get("/warehouses/{warehouse_id}")
def lookup_warehouse(warehouse_id: int, db: Database, active_only: bool = False):
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None or (active_only and not warehouse.is_active):
        raise HTTPException(404, "Warehouse not found.")
    return warehouse


@router.get("/bins/{bin_id}")
def lookup_bin(bin_id: int, db: Database, warehouse_id: int | None = None):
    bin_row = db.get(Bin, bin_id)
    if bin_row is None or (warehouse_id is not None and bin_row.warehouse_id != warehouse_id):
        raise HTTPException(404, "Bin not found.")
    return bin_row


@router.get("/bins", response_model=list[BinOut])
def lookup_bins(
    db: Database,
    warehouse_id: int,
    ids: list[int] = Query(..., min_length=1, max_length=100),
):
    return db.scalars(
        select(Bin).where(Bin.id.in_(set(ids)), Bin.warehouse_id == warehouse_id).order_by(Bin.id)
    ).all()

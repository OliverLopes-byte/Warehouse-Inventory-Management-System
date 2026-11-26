from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.catalog_service import required_row, save
from app.database import Database
from app.identity_client import Admin, CurrentUser
from app.models import Bin, Warehouse
from app.schemas import BinInput, BinOut, WarehouseInput, WarehouseOut


router = APIRouter(tags=["Facilities"])


@router.get("/warehouses", response_model=list[WarehouseOut])
def list_warehouses(db: Database, user: CurrentUser):
    return db.scalars(select(Warehouse).order_by(Warehouse.code)).all()


@router.post("/warehouses", response_model=WarehouseOut, status_code=status.HTTP_201_CREATED)
def create_warehouse(body: WarehouseInput, db: Database, admin: Admin):
    values = body.model_dump()
    values["code"] = body.code.strip().upper()
    return save(db, Warehouse(), values)


@router.put("/warehouses/{warehouse_id}", response_model=WarehouseOut)
def update_warehouse(warehouse_id: int, body: WarehouseInput, db: Database, admin: Admin):
    row = required_row(db, Warehouse, warehouse_id, "Warehouse")
    values = body.model_dump()
    values["code"] = body.code.strip().upper()
    return save(db, row, values)


@router.get("/warehouses/{warehouse_id}/bins", response_model=list[BinOut])
def list_bins(warehouse_id: int, db: Database, user: CurrentUser):
    if user.role != "ADMIN" and user.warehouse_id != warehouse_id:
        raise HTTPException(403, "You can only view bins for your home warehouse.")
    required_row(db, Warehouse, warehouse_id, "Warehouse")
    return db.scalars(
        select(Bin).where(Bin.warehouse_id == warehouse_id).order_by(Bin.code)
    ).all()


@router.post("/warehouses/{warehouse_id}/bins", response_model=BinOut, status_code=status.HTTP_201_CREATED)
def create_bin(warehouse_id: int, body: BinInput, db: Database, admin: Admin):
    required_row(db, Warehouse, warehouse_id, "Warehouse")
    return save(db, Bin(warehouse_id=warehouse_id), {"code": body.code.strip().upper()})


@router.put("/warehouses/{warehouse_id}/bins/{bin_id}", response_model=BinOut)
def update_bin(warehouse_id: int, bin_id: int, body: BinInput, db: Database, admin: Admin):
    row = required_row(db, Bin, bin_id, "Bin")
    if row.warehouse_id != warehouse_id:
        raise HTTPException(404, "Bin not found in this warehouse.")
    return save(db, row, {"code": body.code.strip().upper()})

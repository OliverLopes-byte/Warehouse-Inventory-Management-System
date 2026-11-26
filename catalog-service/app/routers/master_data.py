from fastapi import APIRouter, status
from sqlalchemy import select

from app.catalog_service import required_row, save
from app.database import Database
from app.identity_client import Admin, CurrentUser
from app.models import Category, Supplier, UOM
from app.schemas import CategoryInput, CategoryOut, SupplierInput, SupplierOut, UOMInput, UOMOut


router = APIRouter(tags=["Master data"])


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Database, user: CurrentUser):
    return db.scalars(select(Category).order_by(Category.name)).all()


@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(body: CategoryInput, db: Database, admin: Admin):
    return save(db, Category(), {"name": body.name.strip()})


@router.put("/categories/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, body: CategoryInput, db: Database, admin: Admin):
    return save(db, required_row(db, Category, category_id, "Category"), {"name": body.name.strip()})


@router.get("/uoms", response_model=list[UOMOut])
def list_uoms(db: Database, user: CurrentUser):
    return db.scalars(select(UOM).order_by(UOM.code)).all()


@router.post("/uoms", response_model=UOMOut, status_code=status.HTTP_201_CREATED)
def create_uom(body: UOMInput, db: Database, admin: Admin):
    return save(db, UOM(), {"code": body.code.strip().upper(), "description": body.description.strip()})


@router.put("/uoms/{uom_id}", response_model=UOMOut)
def update_uom(uom_id: int, body: UOMInput, db: Database, admin: Admin):
    row = required_row(db, UOM, uom_id, "Unit of measure")
    return save(db, row, {"code": body.code.strip().upper(), "description": body.description.strip()})


@router.get("/suppliers", response_model=list[SupplierOut])
def list_suppliers(db: Database, user: CurrentUser):
    return db.scalars(select(Supplier).order_by(Supplier.name, Supplier.id)).all()


@router.post("/suppliers", response_model=SupplierOut, status_code=status.HTTP_201_CREATED)
def create_supplier(body: SupplierInput, db: Database, admin: Admin):
    values = body.model_dump()
    values["email"] = str(body.email).lower()
    return save(db, Supplier(), values)


@router.put("/suppliers/{supplier_id}", response_model=SupplierOut)
def update_supplier(supplier_id: int, body: SupplierInput, db: Database, admin: Admin):
    row = required_row(db, Supplier, supplier_id, "Supplier")
    values = body.model_dump()
    values["email"] = str(body.email).lower()
    return save(db, row, values)

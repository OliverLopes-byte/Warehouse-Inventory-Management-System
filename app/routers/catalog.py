from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select

from app.db import Database
from app.models import Bin, Category, Product, Supplier, UOM, Warehouse
from app.queries import PageNumber, PageSize, page_of, required_row
from app.schemas import BinInput, BinOut, CategoryInput, CategoryOut, Page, ProductInput
from app.schemas import ProductOut, SupplierInput, SupplierOut, UOMInput, UOMOut, WarehouseInput, WarehouseOut
from app.security import Admin, CurrentUser


router = APIRouter(tags=["Master data"])


def save_master(db, row, values):
    for field, value in values.items():
        setattr(row, field, value)
    db.add(row)
    db.commit()
    return row


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Database, user: CurrentUser):
    return db.scalars(select(Category).order_by(Category.name)).all()


@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(body: CategoryInput, db: Database, admin: Admin):
    return save_master(db, Category(), body.model_dump())


@router.put("/categories/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, body: CategoryInput, db: Database, admin: Admin):
    return save_master(db, required_row(db, Category, category_id, "Category"), body.model_dump())


@router.get("/uoms", response_model=list[UOMOut])
def list_uoms(db: Database, user: CurrentUser):
    return db.scalars(select(UOM).order_by(UOM.code)).all()


@router.post("/uoms", response_model=UOMOut, status_code=status.HTTP_201_CREATED)
def create_uom(body: UOMInput, db: Database, admin: Admin):
    return save_master(db, UOM(), {"code": body.code.upper(), "description": body.description})


@router.put("/uoms/{uom_id}", response_model=UOMOut)
def update_uom(uom_id: int, body: UOMInput, db: Database, admin: Admin):
    uom = required_row(db, UOM, uom_id, "Unit of measure")
    return save_master(db, uom, {"code": body.code.upper(), "description": body.description})


@router.get("/products", response_model=Page[ProductOut])
def search_products(
    db: Database, user: CurrentUser,
    sku: Annotated[str | None, Query(max_length=40)] = None,
    name: Annotated[str | None, Query(max_length=120)] = None,
    category_id: Annotated[int | None, Query(gt=0)] = None,
    page: PageNumber = 1, size: PageSize = 25,
):
    statement = select(Product).where(Product.is_deleted.is_(False))
    if sku:
        statement = statement.where(Product.sku.icontains(sku.strip(), autoescape=True))
    if name:
        statement = statement.where(Product.name.icontains(name.strip(), autoescape=True))
    if category_id is not None:
        statement = statement.where(Product.category_id == category_id)
    return page_of(db, statement.order_by(Product.sku, Product.id), page, size)


@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Database, user: CurrentUser):
    product = required_row(db, Product, product_id, "Product")
    if product.is_deleted:
        raise HTTPException(404, "Product not found.")
    return product


def save_product(body: ProductInput, db: Database, product: Product):
    required_row(db, Category, body.category_id, "Category")
    required_row(db, UOM, body.uom_id, "Unit of measure")
    return save_master(db, product, {**body.model_dump(), "sku": body.sku.upper()})


@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(body: ProductInput, db: Database, admin: Admin):
    return save_product(body, db, Product())


@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, body: ProductInput, db: Database, admin: Admin):
    return save_product(body, db, get_product(product_id, db, admin))


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_product(product_id: int, db: Database, admin: Admin):
    product = required_row(db, Product, product_id, "Product")
    product.is_deleted = True
    db.commit()
    return Response(status_code=204)


@router.get("/suppliers", response_model=list[SupplierOut])
def list_suppliers(db: Database, user: CurrentUser):
    return db.scalars(select(Supplier).order_by(Supplier.name, Supplier.id)).all()


@router.post("/suppliers", response_model=SupplierOut, status_code=status.HTTP_201_CREATED)
def create_supplier(body: SupplierInput, db: Database, admin: Admin):
    return save_master(db, Supplier(), body.model_dump())


@router.put("/suppliers/{supplier_id}", response_model=SupplierOut)
def update_supplier(supplier_id: int, body: SupplierInput, db: Database, admin: Admin):
    return save_master(db, required_row(db, Supplier, supplier_id, "Supplier"), body.model_dump())


@router.get("/warehouses", response_model=list[WarehouseOut])
def list_warehouses(db: Database, user: CurrentUser):
    return db.scalars(select(Warehouse).order_by(Warehouse.code)).all()


@router.post("/warehouses", response_model=WarehouseOut, status_code=status.HTTP_201_CREATED)
def create_warehouse(body: WarehouseInput, db: Database, admin: Admin):
    return save_master(db, Warehouse(), {**body.model_dump(), "code": body.code.upper()})


@router.put("/warehouses/{warehouse_id}", response_model=WarehouseOut)
def update_warehouse(warehouse_id: int, body: WarehouseInput, db: Database, admin: Admin):
    warehouse = required_row(db, Warehouse, warehouse_id, "Warehouse")
    return save_master(db, warehouse, {**body.model_dump(), "code": body.code.upper()})


@router.get("/warehouses/{warehouse_id}/bins", response_model=list[BinOut])
def list_bins(warehouse_id: int, db: Database, user: CurrentUser):
    if user.warehouse_id != warehouse_id and user.role != "ADMIN":
        raise HTTPException(403, "You can only view bins for your home warehouse.")
    required_row(db, Warehouse, warehouse_id, "Warehouse")
    return db.scalars(select(Bin).where(Bin.warehouse_id == warehouse_id).order_by(Bin.code)).all()


@router.post("/warehouses/{warehouse_id}/bins", response_model=BinOut, status_code=status.HTTP_201_CREATED)
def create_bin(warehouse_id: int, body: BinInput, db: Database, admin: Admin):
    required_row(db, Warehouse, warehouse_id, "Warehouse")
    return save_master(db, Bin(warehouse_id=warehouse_id), {"code": body.code.upper()})


@router.put("/warehouses/{warehouse_id}/bins/{bin_id}", response_model=BinOut)
def update_bin(warehouse_id: int, bin_id: int, body: BinInput, db: Database, admin: Admin):
    bin_row = required_row(db, Bin, bin_id, "Bin")
    if bin_row.warehouse_id != warehouse_id:
        raise HTTPException(404, "Bin not found in this warehouse.")
    return save_master(db, bin_row, {"code": body.code.upper()})

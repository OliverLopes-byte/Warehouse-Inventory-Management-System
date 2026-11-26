from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select

from app.catalog_service import page_of, required_row, save
from app.database import Database
from app.identity_client import Admin, CurrentUser
from app.models import Category, Product, UOM
from app.schemas import Page, ProductInput, ProductOut


router = APIRouter(tags=["Products"])


@router.get("/products", response_model=Page[ProductOut])
def search_products(
    db: Database,
    user: CurrentUser,
    sku: Annotated[str | None, Query(max_length=40)] = None,
    name: Annotated[str | None, Query(max_length=120)] = None,
    category_id: Annotated[int | None, Query(gt=0)] = None,
    page: Annotated[int, Query(ge=1, le=1_000_000)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 25,
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
    values = body.model_dump()
    values["sku"] = body.sku.strip().upper()
    values["name"] = body.name.strip()
    return save(db, product, values)


@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(body: ProductInput, db: Database, admin: Admin):
    return save_product(body, db, Product())


@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, body: ProductInput, db: Database, admin: Admin):
    product = get_product(product_id, db, admin)
    return save_product(body, db, product)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_product(product_id: int, db: Database, admin: Admin):
    product = required_row(db, Product, product_id, "Product")
    product.is_deleted = True
    db.commit()
    return Response(status_code=204)

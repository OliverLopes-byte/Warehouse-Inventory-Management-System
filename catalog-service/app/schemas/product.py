from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PositiveInt

from app.schemas.input import Input


class ProductInput(Input):
    sku: Annotated[str, Field(min_length=1, max_length=40)]
    name: Annotated[str, Field(min_length=1, max_length=120)]
    category_id: PositiveInt
    uom_id: PositiveInt
    reorder_level: Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=3)]
    unit_cost: Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]


class ProductOut(ProductInput):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_deleted: bool


class ProductReference(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    reorder_level: Decimal
    unit_cost: Decimal
    is_deleted: bool

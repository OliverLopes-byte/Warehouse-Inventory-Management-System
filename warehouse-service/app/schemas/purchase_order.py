from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PositiveInt

from app.schemas.input import Input
from app.models.enums import POStatus


class POItemInput(Input):
    product_id: PositiveInt
    ordered_qty: Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=3)]
    unit_price: Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]


class POCreate(Input):
    po_no: Annotated[str, Field(min_length=1, max_length=40)]
    supplier_id: PositiveInt
    ordered_on: date
    items: Annotated[list[POItemInput], Field(min_length=1, max_length=100)]


class POItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    ordered_qty: Decimal
    received_qty: Decimal
    unit_price: Decimal
    outstanding_qty: Decimal


class POOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    po_no: str
    supplier_id: int
    warehouse_id: int
    status: POStatus
    ordered_on: date
    total_amount: Decimal
    items: list[POItemOut]

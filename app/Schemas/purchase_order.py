from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import Field, PositiveInt

from app.models import POStatus
from app.Schemas.fields import DocumentNumber, Money, PositiveQuantity
from app.Schemas.input import Input


class POItemInput(Input):
    product_id: PositiveInt
    ordered_qty: PositiveQuantity
    unit_price: Money


class POCreate(Input):
    po_no: DocumentNumber
    supplier_id: PositiveInt
    ordered_on: date
    items: Annotated[list[POItemInput], Field(min_length=1, max_length=100)]


class POItemOut(POItemInput):
    id: int
    received_qty: Decimal
    outstanding_qty: Decimal


class POOut(Input):
    id: int
    po_no: str
    supplier_id: int
    warehouse_id: int
    status: POStatus
    ordered_on: date
    total_amount: Decimal
    items: list[POItemOut]

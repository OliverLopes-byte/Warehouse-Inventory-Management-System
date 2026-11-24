from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class ReorderOut(BaseModel):
    product_id: int
    sku: str
    name: str
    quantity: Decimal
    reorder_level: Decimal


class ExpiryOut(BaseModel):
    product_id: int
    sku: str
    name: str
    quantity: Decimal
    expiry_on: date
    status: str

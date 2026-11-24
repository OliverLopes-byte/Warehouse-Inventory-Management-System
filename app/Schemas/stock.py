from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, PositiveInt

from app.models import Movement
from app.Schemas.fields import DocumentNumber, PositiveQuantity, Quantity
from app.Schemas.input import Input


class IssueInput(Input):
    product_id: PositiveInt
    quantity: PositiveQuantity
    requisition_no: DocumentNumber


class TransferInput(Input):
    product_id: PositiveInt
    source_warehouse_id: PositiveInt
    destination_warehouse_id: PositiveInt
    quantity: PositiveQuantity


class AdjustmentInput(Input):
    product_id: PositiveInt
    counted_quantity: Quantity
    reason: Annotated[str, Field(min_length=1, max_length=500)]


class LedgerOut(Input):
    id: int
    product_id: int
    warehouse_id: int
    movement_type: Movement
    qty_delta: Decimal
    reference_type: str
    reference_id: str
    balance_after: Decimal
    position_seq: int
    reason: str | None
    created_by: int
    created_at: datetime


class TransferOut(BaseModel):
    reference_id: str
    out: LedgerOut
    incoming: LedgerOut


class BalanceOut(BaseModel):
    product_id: int
    sku: str
    product_name: str
    warehouse_id: int
    warehouse_code: str
    quantity: Decimal
    position_seq: int
    expiry_on: date | None


class ExpiryInput(Input):
    expiry_on: date | None

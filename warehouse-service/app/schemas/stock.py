from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PositiveInt

from app.schemas.input import Input
from app.models.enums import Movement


class IssueInput(Input):
    product_id: PositiveInt
    quantity: Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=3)]
    requisition_no: Annotated[str, Field(min_length=1, max_length=40)]


class TransferInput(Input):
    product_id: PositiveInt
    source_warehouse_id: PositiveInt
    destination_warehouse_id: PositiveInt
    quantity: Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=3)]


class AdjustmentInput(Input):
    product_id: PositiveInt
    counted_quantity: Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=3)]
    reason: Annotated[str, Field(min_length=1, max_length=500)]


class ExpiryInput(Input):
    expiry_on: date | None


class LedgerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class InternalBalance(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    warehouse_id: int
    quantity: Decimal
    position_seq: int
    expiry_on: date | None

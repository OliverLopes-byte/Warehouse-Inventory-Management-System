from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PositiveInt

from app.schemas.input import Input


class GRNItemInput(Input):
    po_item_id: PositiveInt
    qty: Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=3)]
    bin_id: PositiveInt


class GRNCreate(Input):
    grn_no: Annotated[str, Field(min_length=1, max_length=40)]
    po_id: PositiveInt
    remark: Annotated[str, Field(max_length=500)] | None = None
    items: Annotated[list[GRNItemInput], Field(min_length=1, max_length=100)]


class GRNItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    po_item_id: int
    qty: Decimal
    bin_id: int
    product_id: int


class GRNOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    grn_no: str
    po_id: int
    received_by: int
    received_on: datetime
    remark: str | None
    items: list[GRNItemOut]

from datetime import datetime
from typing import Annotated

from pydantic import Field, PositiveInt

from app.Schemas.fields import DocumentNumber, PositiveQuantity
from app.Schemas.input import Input


class GRNItemInput(Input):
    po_item_id: PositiveInt
    qty: PositiveQuantity
    bin_id: PositiveInt


class GRNCreate(Input):
    grn_no: DocumentNumber
    po_id: PositiveInt
    remark: Annotated[str, Field(max_length=500)] | None = None
    items: Annotated[list[GRNItemInput], Field(min_length=1, max_length=100)]


class GRNItemOut(GRNItemInput):
    id: int
    product_id: int


class GRNOut(Input):
    id: int
    grn_no: str
    po_id: int
    received_by: int
    received_on: datetime
    remark: str | None
    items: list[GRNItemOut]

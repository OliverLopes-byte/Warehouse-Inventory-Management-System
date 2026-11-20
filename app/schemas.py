from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, PositiveInt, StringConstraints

from app.models import Movement, POStatus, Role


Code = Annotated[str, Field(min_length=1, max_length=24)]
DocumentNumber = Annotated[str, Field(min_length=1, max_length=40)]
Name = Annotated[str, Field(min_length=1, max_length=120)]
Quantity = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=3)]
PositiveQuantity = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=3)]
Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
T = TypeVar("T")


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    page: int
    size: int
    total: int


class UserCreate(Input):
    email: EmailStr
    password: Annotated[str, StringConstraints(min_length=12, max_length=128, strip_whitespace=False)]
    full_name: Name
    role: Role
    warehouse_id: PositiveInt | None = None


class UserOut(Input):
    id: int
    email: EmailStr
    full_name: str
    role: Role
    warehouse_id: int | None
    is_active: bool


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CategoryInput(Input):
    name: Annotated[str, Field(min_length=1, max_length=100)]


class CategoryOut(CategoryInput):
    id: int


class UOMInput(Input):
    code: Code
    description: Name


class UOMOut(UOMInput):
    id: int


class ProductInput(Input):
    sku: DocumentNumber
    name: Name
    category_id: PositiveInt
    uom_id: PositiveInt
    reorder_level: Quantity
    unit_cost: Money


class ProductOut(ProductInput):
    id: int
    is_deleted: bool


class SupplierInput(Input):
    name: Name
    email: EmailStr
    phone: Annotated[str, Field(min_length=1, max_length=40)]
    address: Annotated[str, Field(min_length=1, max_length=250)]
    payment_terms: Name
    is_active: bool = True


class SupplierOut(SupplierInput):
    id: int


class WarehouseInput(Input):
    code: Code
    name: Name
    city: Annotated[str, Field(min_length=1, max_length=100)]
    is_active: bool = True


class WarehouseOut(WarehouseInput):
    id: int


class BinInput(Input):
    code: Code


class BinOut(BinInput):
    id: int
    warehouse_id: int


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


class ValuationOut(BaseModel):
    warehouse_id: int
    warehouse_code: str
    warehouse_name: str
    value: Decimal


class MovementAnalysisOut(BaseModel):
    product_id: int
    sku: str
    name: str
    issued_quantity: Decimal
    classification: str

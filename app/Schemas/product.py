from pydantic import PositiveInt

from app.Schemas.fields import DocumentNumber, Money, Name, Quantity
from app.Schemas.input import Input


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

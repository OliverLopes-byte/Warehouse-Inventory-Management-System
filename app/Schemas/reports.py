from decimal import Decimal

from pydantic import BaseModel


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

from app.Schemas.fields import Code
from app.Schemas.input import Input


class BinInput(Input):
    code: Code


class BinOut(BinInput):
    id: int
    warehouse_id: int
